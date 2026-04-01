"""Specialized agent registry — multiple agents with different roles and tool sets.

The router picks the best agent for a given task using keyword + LLM scoring.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class AgentSpec:
    id: str
    name: str
    role: str
    description: str
    tools: list[str]
    system_prompt: str
    keywords: list[str]
    color: str  # for dashboard badge
    icon: str


# ── Specialized agent definitions ────────────────────────────────────────────

CODE_AGENT = AgentSpec(
    id="code_agent",
    name="CodeAgent",
    role="Software Engineer",
    description="Writes, executes, and debugs code. Saves artifacts to Filecoin.",
    tools=["code", "filecoin"],
    keywords=["write", "code", "script", "function", "program", "python", "javascript",
              "debug", "fix", "implement", "build", "generate", "file", "save", "run"],
    color="indigo",
    icon="⌨",
    system_prompt="""You are CodeAgent, a specialized AI software engineer.
Your job: write clean, working code and save the output files.

Workflow: plan -> write code -> execute -> verify output -> store on Filecoin.

Available tools:
- code: write/read/execute files. Params: {operation: write|read|run|list, filename, content}
- filecoin: store results. Params: {operation: store, key, filename}

CRITICAL: Always respond with raw JSON only. No markdown fences.
Example: {"action": "code", "params": {"operation": "write", "filename": "solution.py", "content": "print('hello')"}}
Or if done: {"action": "done", "result": "Created solution.py with hello world"}""",
)

RESEARCH_AGENT = AgentSpec(
    id="research_agent",
    name="ResearchAgent",
    role="Research Analyst",
    description="Searches the web, fetches URLs, summarizes content. Stores findings in Storacha.",
    tools=["web", "storacha"],
    keywords=["search", "find", "research", "look up", "what is", "who is", "explain",
              "summarize", "fetch", "url", "website", "news", "latest", "current", "learn"],
    color="cyan",
    icon="🔍",
    system_prompt="""You are ResearchAgent, a specialized AI research analyst.
Your job: search the web, fetch pages, summarize findings, and store knowledge.

Workflow: search -> fetch details -> synthesize -> store in memory.

Available tools:
- web: search and fetch. Params: {operation: search|fetch, query, url}
- storacha: store findings. Params: {operation: remember, key, value, category}

CRITICAL: Always respond with raw JSON only. No markdown fences.
Example: {"action": "web", "params": {"operation": "search", "query": "latest AI news"}}
Or if done: {"action": "done", "result": "Found and stored 3 key findings"}""",
)

BLOCKCHAIN_AGENT = AgentSpec(
    id="blockchain_agent",
    name="BlockchainAgent",
    role="Web3 Engineer",
    description="Executes on-chain operations, reads contracts, manages identity and reputation.",
    tools=["blockchain", "wallet", "identity"],
    keywords=["blockchain", "contract", "transaction", "wallet", "eth", "token", "onchain",
              "deploy", "sign", "balance", "address", "erc", "reputation", "trust", "sepolia"],
    color="purple",
    icon="⛓",
    system_prompt="""You are BlockchainAgent, a specialized Web3 AI engineer.
Your job: interact with smart contracts, manage wallet operations, and handle onchain identity.

Workflow: validate -> prepare transaction -> sign -> verify on-chain.

Available tools:
- blockchain: read/write contracts. Params: {operation: call|send|balance, contract, method, args}
- wallet: wallet ops. Params: {operation: status|balance|sign_message|sign_transaction}
- identity: ERC-8004 reputation. Params: {operation: get_reputation|set_trust, target_id, score}

CRITICAL: Always respond with raw JSON only. No markdown fences.
Example: {"action": "wallet", "params": {"operation": "balance", "chain": "sepolia"}}
Or if done: {"action": "done", "result": "Transaction completed: 0xabc..."}""",
)

FULL_AGENT = AgentSpec(
    id="full_agent",
    name="FullAgent",
    role="Autonomous Orchestrator",
    description="All tools available. Handles complex multi-step tasks requiring code, research, and blockchain ops.",
    tools=["code", "web", "blockchain", "wallet", "identity", "filecoin", "storacha", "github"],
    keywords=[],  # fallback — matches everything
    color="green",
    icon="🤖",
    system_prompt="""You are AgentProof, a fully autonomous AI agent with verifiable onchain identity.
You have access to all tools and handle complex multi-step tasks.

Workflow: discover -> plan -> execute -> verify -> submit.

Available tools:
- code: {operation: write|read|run|list, filename, content}
- web: {operation: search|fetch, query, url}
- blockchain: {operation: call|send|balance, contract, method, args}
- wallet: {operation: status|balance|sign_message}
- identity: {operation: get_reputation|set_trust}
- filecoin: {operation: store|retrieve|list, key, filename}
- storacha: {operation: remember|recall|context, key, value, category}
- github: {operation: search|get_repo|create_issue, query, repo, title, body}

CRITICAL: Always respond with raw JSON only. No markdown fences.
Example: {"action": "code", "params": {"operation": "write", "filename": "main.py", "content": "..."}}
Or if done: {"action": "done", "result": "Task completed successfully"}""",
)

# Registry — order matters for keyword matching
AGENT_REGISTRY: list[AgentSpec] = [
    CODE_AGENT,
    RESEARCH_AGENT,
    BLOCKCHAIN_AGENT,
    FULL_AGENT,
]


def route_task(task: str) -> AgentSpec:
    """Pick the best agent for a task based on keyword scoring.

    Falls back to FullAgent if no clear winner.
    """
    task_lower = task.lower()
    scores: dict[str, int] = {}

    for spec in AGENT_REGISTRY:
        if not spec.keywords:  # FullAgent — skip, it's the fallback
            continue
        score = sum(1 for kw in spec.keywords if kw in task_lower)
        scores[spec.id] = score

    if not scores or max(scores.values()) == 0:
        return FULL_AGENT

    best_id = max(scores, key=lambda k: scores[k])
    return next(s for s in AGENT_REGISTRY if s.id == best_id)


def get_all_specs() -> list[dict[str, Any]]:
    """Return all agent specs as JSON-serializable dicts for the dashboard."""
    return [
        {
            "id": s.id,
            "name": s.name,
            "role": s.role,
            "description": s.description,
            "tools": s.tools,
            "color": s.color,
            "icon": s.icon,
            "keywords": s.keywords,
        }
        for s in AGENT_REGISTRY
    ]
