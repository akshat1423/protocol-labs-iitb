"""AgentProof — Core autonomous agent loop.

Implements the discover -> plan -> execute -> verify -> submit cycle.
"""

from __future__ import annotations

import asyncio
import json
import time
from pathlib import Path
from typing import Any

from .config import config
from .guardrails import Guardrails
from .llm import LLMClient
from .logger import ExecutionLogger
from .models import (
    AgentIdentity,
    BudgetTracker,
    LogLevel,
    Task,
    TaskStatus,
)

SYSTEM_PROMPT = """You are AgentProof, an autonomous AI agent with a verifiable onchain identity.
You operate independently through a full decision loop: discover -> plan -> execute -> verify.

Your capabilities:
- Discover problems and tasks from data sources
- Plan multi-step solutions with task decomposition
- Execute using real tools (code generation, APIs, blockchain transactions)
- Verify your own outputs before submission
- Self-correct when errors occur

You must:
- Operate within your compute budget
- Log all decisions transparently
- Validate actions before executing them (especially irreversible ones)
- Produce structured, verifiable outputs

CRITICAL: Always respond with raw JSON only. No markdown, no code fences, no explanation text.
Just the JSON object, nothing else."""


def _clean_json(text: str) -> str:
    """Strip markdown code fences and extra text around JSON."""
    text = text.strip()
    # Remove ```json ... ``` wrapping
    if text.startswith("```"):
        lines = text.split("\n")
        # Remove first line (```json) and last line (```)
        start = 1
        end = len(lines)
        for i in range(len(lines) - 1, 0, -1):
            if lines[i].strip() == "```":
                end = i
                break
        text = "\n".join(lines[start:end]).strip()

    # Try to find JSON object or array boundaries
    for start_char, end_char in [("{", "}"), ("[", "]")]:
        first = text.find(start_char)
        last = text.rfind(end_char)
        if first != -1 and last != -1 and last > first:
            candidate = text[first:last + 1]
            try:
                json.loads(candidate)
                return candidate
            except json.JSONDecodeError:
                continue

    return text


class AgentProof:
    """Core autonomous agent with verifiable execution."""

    def __init__(self):
        self.budget = BudgetTracker(
            max_usd=config.compute_budget_usd,
            max_llm_calls=config.max_llm_calls,
            max_tool_calls=config.max_tool_calls,
        )
        self.logger = ExecutionLogger(output_path="agent_log.json")
        self.guardrails = Guardrails(self.budget, self.logger)
        self.llm = LLMClient(self.budget)
        self.identity = AgentIdentity(
            agent_name=config.agent_name,
            operator_wallet="",  # Set after wallet setup
            capabilities=["code_generation", "api_integration", "blockchain_tx"],
            supported_tools=[],  # Populated by register_tool()
            compute_constraints={"max_usd": config.compute_budget_usd},
        )
        self.tasks: list[Task] = []
        self.current_task: Task | None = None
        self._running = False
        self._tools: dict[str, Any] = {}

        # Integrations (set via attach_* methods)
        self.erc8004 = None
        self.filecoin = None
        self.storacha = None
        self.lit = None

    def register_tool(self, name: str, handler):
        """Register a tool the agent can use during execution."""
        self._tools[name] = handler
        if name not in self.identity.supported_tools:
            self.identity.supported_tools.append(name)

    def attach_erc8004(self, erc8004):
        """Attach ERC-8004 identity integration."""
        self.erc8004 = erc8004
        self.identity.operator_wallet = erc8004.operator_address

    def attach_filecoin(self, filecoin):
        """Attach Filecoin storage integration."""
        self.filecoin = filecoin

    def attach_storacha(self, storacha):
        """Attach Storacha memory integration."""
        self.storacha = storacha

    def attach_lit(self, lit):
        """Attach Lit Protocol wallet integration."""
        self.lit = lit

    async def _initialize_integrations(self):
        """Initialize all attached integrations on startup."""
        # Load persistent memory
        if self.storacha:
            await self.storacha.initialize()
            context = await self.storacha.get_context()
            self.logger.info("init", f"Memory loaded: {len(context)} chars")

        # Register ERC-8004 identity if not already done
        if self.erc8004 and not self.erc8004.token_id:
            self.logger.info("init", "Registering onchain identity...")
            result = await self.erc8004.register(
                self.identity.agent_name,
                "ipfs://agent-manifest-placeholder",
            )
            if "error" not in result:
                self.identity.erc8004_token_id = str(result.get("token_id"))
                self.identity.erc8004_tx_hash = result.get("tx_hash")
                self.logger.info(
                    "init",
                    f"Identity registered: token={result.get('token_id')} tx={result.get('tx_hash')}",
                )
            else:
                self.logger.error("init", f"Identity registration failed: {result['error']}")

        # Initialize Lit Protocol wallet
        if self.lit:
            result = await self.lit.initialize()
            if "error" not in result:
                self.logger.info("init", f"Lit wallet: {result.get('address', 'unknown')}")
            else:
                self.logger.info("init", f"Lit wallet fallback: {result.get('fallback', 'none')}")

    async def _save_state(self):
        """Persist agent state to Filecoin and Storacha."""
        state = self.get_state()

        if self.filecoin:
            await self.filecoin.store_agent_state(state)
            # Also store execution logs
            log_data = {
                "entries": self.logger.get_recent(500),
                "chain_head": self.logger._last_hash,
                "chain_valid": self.logger.verify_chain(),
            }
            await self.filecoin.store_execution_log(log_data)

        if self.storacha:
            await self.storacha.remember(
                "last_state",
                {
                    "tasks_completed": sum(1 for t in self.tasks if t.status == TaskStatus.COMPLETED),
                    "tasks_failed": sum(1 for t in self.tasks if t.status == TaskStatus.FAILED),
                    "budget": self.budget.summary(),
                },
                category="state",
            )

    async def run(self, initial_task: str | None = None):
        """Main agent loop — runs autonomously until budget exhausted or paused."""
        self._running = True
        self.logger.info("init", f"AgentProof starting: {self.identity.agent_name}")
        self.logger.info("init", f"Budget: {self.budget.summary()}")

        # Initialize integrations
        await self._initialize_integrations()

        try:
            if initial_task:
                task = Task(
                    title=initial_task,
                    description=initial_task,
                    source="user_input",
                )
                self.tasks.append(task)
            else:
                # Discovery phase
                await self._discover()

            # Process tasks
            while self._running and self.tasks and self.budget.can_spend():
                if self.guardrails.is_paused:
                    self.logger.info("pause", "Agent paused, waiting...")
                    await asyncio.sleep(1)
                    continue

                task = self._next_task()
                if not task:
                    break

                self.current_task = task
                await self._process_task(task)

        except Exception as e:
            self.logger.error("fatal", f"Agent crashed: {str(e)}", data={"error": str(e)})
        finally:
            self._running = False
            self.logger.info("shutdown", f"Agent stopped. {self.budget.summary()}")
            await self._save_state()
            self.logger.save()
            self._save_manifest()

    async def _discover(self):
        """Discover tasks from available data sources."""
        self.logger.info("discover", "Scanning for tasks...")

        prompt = """Analyze available data sources and identify a meaningful task to work on.
Consider: GitHub issues, hackathon challenges, API integrations, or code improvements.
Respond with a JSON task definition:
{
    "title": "short task title",
    "description": "detailed description of what to do",
    "source": "where you found this task",
    "plan": ["step 1", "step 2", ...]
}"""

        response = self.llm.complete_sync(SYSTEM_PROMPT, prompt)
        self.logger.decision("discover", f"Discovery result: {response[:200]}")

        try:
            task_def = json.loads(_clean_json(response))
            task = Task(
                title=task_def.get("title", "Discovered Task"),
                description=task_def.get("description", ""),
                source=task_def.get("source", "llm_discovery"),
                plan=task_def.get("plan", []),
            )
            self.tasks.append(task)
            self.logger.info("discover", f"Found task: {task.title}")
        except json.JSONDecodeError:
            # LLM didn't return clean JSON — extract what we can
            task = Task(
                title="LLM-Discovered Task",
                description=response[:500],
                source="llm_discovery",
            )
            self.tasks.append(task)

    async def _process_task(self, task: Task):
        """Run a task through the full lifecycle: plan -> execute -> verify."""
        self.logger.info("task", f"Processing: {task.title}", task_id=task.task_id)

        try:
            # Plan
            task.status = TaskStatus.PLANNING
            plan = await self._plan(task)
            task.plan = plan

            # Execute
            task.status = TaskStatus.EXECUTING
            outputs = await self._execute(task)
            task.outputs = outputs

            # Verify
            task.status = TaskStatus.VERIFYING
            verified = await self._verify(task)

            if verified:
                task.status = TaskStatus.COMPLETED
                task.completed_at = time.time()
                self.logger.info("complete", f"Task completed: {task.title}", task_id=task.task_id)
                # Record onchain
                if self.erc8004:
                    await self.erc8004.record_task_completed()
                # Save memory
                if self.storacha:
                    await self.storacha.remember_conversation(
                        task.task_id,
                        [{"role": "task", "content": task.to_dict()}],
                    )
            else:
                task.status = TaskStatus.FAILED
                task.error = "Verification failed"
                self.logger.error("verify", "Task failed verification", task_id=task.task_id)
                if self.erc8004:
                    await self.erc8004.record_task_failed()

        except Exception as e:
            task.status = TaskStatus.FAILED
            task.error = str(e)
            self.logger.error("task", f"Task failed: {e}", task_id=task.task_id)
            if self.erc8004:
                await self.erc8004.record_task_failed()

    async def _plan(self, task: Task) -> list[str]:
        """Plan the execution steps for a task."""
        self.logger.info("plan", f"Planning: {task.title}", task_id=task.task_id)

        if task.plan:
            self.logger.info("plan", f"Using existing plan with {len(task.plan)} steps", task_id=task.task_id)
            return task.plan

        prompt = f"""Create a detailed execution plan for this task:

Title: {task.title}
Description: {task.description}

Available tools: {list(self._tools.keys())}
Budget remaining: {self.budget.summary()}

Respond with a JSON array of step descriptions:
["step 1 description", "step 2 description", ...]

Keep it to 3-7 concrete, actionable steps."""

        response = self.llm.complete_sync(SYSTEM_PROMPT, prompt)
        self.logger.decision("plan", f"Plan: {response[:300]}", task_id=task.task_id)

        try:
            plan = json.loads(_clean_json(response))
            if isinstance(plan, list):
                return plan
        except json.JSONDecodeError:
            pass

        return [task.description]

    async def _execute(self, task: Task) -> list[dict]:
        """Execute the planned steps using available tools."""
        outputs = []

        for i, step in enumerate(task.plan):
            if not self.budget.can_spend():
                self.logger.guardrail(f"Budget exhausted at step {i+1}", task_id=task.task_id)
                break

            if self.guardrails.is_paused:
                self.logger.info("pause", "Execution paused", task_id=task.task_id)
                break

            self.logger.info("execute", f"Step {i+1}/{len(task.plan)}: {step}", task_id=task.task_id)

            # Ask LLM what tool to use for this step
            tool_docs = """TOOL API REFERENCE (use these EXACT param formats):

- code: {{"operation": "write_file", "filename": "name.py", "content": "file content here"}}
  NOTE: filename is relative to workspace. Use JUST the filename like "script.py", NOT "agent_workspace/script.py"
- code: {{"operation": "read_file", "filename": "name.py"}}
- code: {{"operation": "run_command", "command": "python fibonacci.py 10"}}
  NOTE: commands run inside the workspace dir. Use JUST the filename, NOT full paths.
- code: {{"operation": "list_files"}}
- github: {{"operation": "search_issues", "query": "search terms"}}
- github: {{"operation": "create_repo", "name": "repo-name", "description": "desc"}}
- web: {{"operation": "fetch", "url": "https://..."}}
- web: {{"operation": "json_api", "url": "https://..."}}
- blockchain: {{"operation": "get_balance", "chain": "sepolia"}}
- blockchain: {{"operation": "chain_info", "chain": "sepolia"}}
- filecoin: {{"operation": "store", "key": "my_data", "data": {{"any": "json data"}}}}
- filecoin: {{"operation": "store", "key": "my_file", "filename": "fibonacci.py"}}  ← uploads a workspace file to Filecoin
- filecoin: {{"operation": "retrieve", "key": "my_data"}}
- storacha: {{"operation": "remember", "key": "k", "value": "v", "category": "general"}}
- storacha: {{"operation": "recall", "key": "k"}}
- identity: {{"operation": "get_reputation"}}
- wallet: {{"operation": "status"}}"""

            prompt = f"""Execute this step of the plan:

Task: {task.title}
Current step ({i+1}/{len(task.plan)}): {step}
Previous outputs: {json.dumps(outputs[-3:], default=str) if outputs else "none"}

{tool_docs}

Respond with ONLY a JSON object (no markdown, no explanation):
{{
    "reasoning": "why this tool/approach",
    "tool": "tool_name",
    "params": {{use exact format from TOOL API REFERENCE above}},
    "expected_output": "what you expect"
}}

If no tool is needed, use "tool": "none"."""

            response = self.llm.complete_sync(SYSTEM_PROMPT, prompt)

            try:
                action = json.loads(_clean_json(response))
                tool_name = action.get("tool", "none")
                params = action.get("params", {})

                if tool_name != "none" and tool_name in self._tools:
                    # Guardrail check
                    check = self.guardrails.validate_action(tool_name, params)
                    if not check.allowed:
                        self.logger.guardrail(
                            f"Blocked: {check.reason}",
                            task_id=task.task_id,
                        )
                        outputs.append({"step": i, "blocked": check.reason})
                        continue

                    # Execute tool
                    self.logger.tool_call(tool_name, params, task_id=task.task_id)
                    try:
                        result = await self._tools[tool_name](params)
                        self.budget.record_tool_call()
                        self.logger.tool_result(tool_name, result, task_id=task.task_id)
                        outputs.append({"step": i, "tool": tool_name, "result": result})
                    except Exception as e:
                        self.logger.error("execute", f"Tool error: {e}", task_id=task.task_id)
                        outputs.append({"step": i, "tool": tool_name, "error": str(e)})
                else:
                    self.logger.decision("execute", f"Decision: {action.get('reasoning', '')}", task_id=task.task_id)
                    outputs.append({"step": i, "decision": action.get("reasoning", "")})

            except json.JSONDecodeError:
                self.logger.info("execute", f"Raw step output: {response[:200]}", task_id=task.task_id)
                outputs.append({"step": i, "raw": response[:500]})

        return outputs

    async def _verify(self, task: Task) -> bool:
        """Verify the task outputs meet the requirements."""
        self.logger.info("verify", f"Verifying: {task.title}", task_id=task.task_id)

        prompt = f"""Verify whether this task was completed successfully:

Task: {task.title}
Description: {task.description}
Plan: {json.dumps(task.plan)}
Outputs: {json.dumps(task.outputs[-5:])}

Respond with ONLY a JSON object (no markdown, no explanation):
{{
    "verified": true,
    "confidence": 0.85,
    "reasoning": "explanation here",
    "issues": []
}}
Set "verified" to true if the CORE task was accomplished (even if optional/bonus steps like GitHub or documentation had issues). Only set false if the primary objective completely failed."""

        response = self.llm.complete_sync(SYSTEM_PROMPT, prompt)
        self.logger.decision("verify", f"Verification: {response[:200]}", task_id=task.task_id)

        try:
            result = json.loads(_clean_json(response))
            return result.get("verified", False)
        except json.JSONDecodeError:
            return "success" in response.lower() or "verified" in response.lower()

    def _next_task(self) -> Task | None:
        """Get the next pending task."""
        for task in self.tasks:
            if task.status == TaskStatus.DISCOVERED:
                return task
        return None

    def _save_manifest(self):
        """Save agent.json manifest."""
        manifest = self.identity.to_manifest()
        Path("agent.json").write_text(json.dumps(manifest, indent=2))

    def get_state(self) -> dict:
        """Get current agent state for dashboard."""
        return {
            "identity": self.identity.to_manifest(),
            "budget": self.budget.summary(),
            "tasks": [t.to_dict() for t in self.tasks],
            "current_task": self.current_task.to_dict() if self.current_task else None,
            "running": self._running,
            "paused": self.guardrails.is_paused,
            "log_count": len(self.logger.entries),
            "chain_valid": self.logger.verify_chain(),
        }
