"""Multi-agent demo — two agents that collaborate with trust-gated interactions.

Agent Alpha: discovers a task, plans and executes it
Agent Beta: evaluates Alpha's work and sets trust score

Both agents have ERC-8004 identities and interact through the onchain trust registry.

Prerequisites:
  - Anvil running on localhost:8545
  - AgentRegistry deployed

Usage:
  python -m agent.core.multi_agent_demo
"""

from __future__ import annotations

import asyncio
import json
import os
import time

# Configure for local Anvil
os.environ["OPERATOR_PRIVATE_KEY"] = "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80"
os.environ["SEPOLIA_RPC_URL"] = "http://localhost:8545"
os.environ["ERC8004_REGISTRY_ADDRESS"] = "0x5FbDB2315678afecb367f032d93F642f64180aa3"

from .models import BudgetTracker, Task, TaskStatus
from .logger import ExecutionLogger
from .guardrails import Guardrails
from .demo import MockLLMClient
from ..integrations.erc8004 import ERC8004Identity
from ..integrations.filecoin_storage import FilecoinStorage
from ..tools.code_tool import CodeTool


class SimpleAgent:
    """Lightweight agent for multi-agent demo."""

    def __init__(self, name: str, role: str):
        self.name = name
        self.role = role
        self.budget = BudgetTracker(max_usd=2.0, max_llm_calls=50, max_tool_calls=20)
        self.logger = ExecutionLogger(output_path=f"{name}_log.json")
        self.guardrails = Guardrails(self.budget, self.logger)
        self.llm = MockLLMClient(self.budget)
        self.erc8004 = ERC8004Identity(self.logger)
        self.filecoin = FilecoinStorage(self.logger)
        self.token_id: int | None = None

    async def register_identity(self):
        """Register this agent's onchain identity."""
        self.logger.info("init", f"Registering {self.name} ({self.role})...")
        result = await self.erc8004.register(
            self.name,
            f"ipfs://{self.name.lower()}-manifest",
        )
        if "error" not in result:
            self.token_id = result.get("token_id")
            self.logger.info(
                "init",
                f"Registered: token={self.token_id} tx={result.get('tx_hash', '')[:16]}...",
            )
        return result


class EvaluatorMockLLM:
    """Mock LLM for the evaluator agent."""

    def __init__(self, budget):
        self.budget = budget

    def complete_sync(self, system_prompt, user_message, temperature=0.7):
        self.budget.record_llm_call(0.001)

        if "evaluate" in user_message.lower() or "review" in user_message.lower():
            return json.dumps({
                "evaluation": {
                    "quality_score": 85,
                    "completeness": True,
                    "issues": [],
                    "recommendation": "Approve — work is solid and well-structured",
                    "trust_score": 82,
                },
                "reasoning": "The agent completed all planned steps, produced structured outputs, maintained hash-chain integrity, and stored artifacts on decentralized storage.",
            })

        return json.dumps({"status": "ok"})


async def run_multi_agent_demo():
    print("""
    ╔═══════════════════════════════════════════════════════╗
    ║      AgentProof — MULTI-AGENT TRUST DEMO              ║
    ║                                                        ║
    ║  Agent Alpha: Builder — discovers & executes tasks     ║
    ║  Agent Beta:  Evaluator — reviews & rates trust        ║
    ║                                                        ║
    ║  Both agents have ERC-8004 onchain identities          ║
    ║  Trust is set based on evaluation of work quality      ║
    ╚═══════════════════════════════════════════════════════╝
    """)

    # ---- Phase 1: Register both agents ----
    print("=" * 60)
    print("PHASE 1: IDENTITY REGISTRATION")
    print("=" * 60)

    alpha = SimpleAgent("AgentProof-Alpha", "builder")
    beta = SimpleAgent("AgentProof-Beta", "evaluator")
    beta.llm = EvaluatorMockLLM(beta.budget)

    await alpha.register_identity()
    await beta.register_identity()

    print(f"\n  Alpha: token_id={alpha.token_id}, operator={alpha.erc8004.operator_address}")
    print(f"  Beta:  token_id={beta.token_id}, operator={beta.erc8004.operator_address}")

    # ---- Phase 2: Alpha executes a task ----
    print("\n" + "=" * 60)
    print("PHASE 2: ALPHA EXECUTES TASK")
    print("=" * 60)

    code_tool = CodeTool()

    # Alpha builds something
    alpha.logger.info("task", "Alpha: Building a utility library")

    steps = [
        ("utils.py", 'def greet(name):\n    return f"Hello, {name}!"\n\ndef add(a, b):\n    return a + b\n'),
        ("test_utils.py", 'from utils import greet, add\nassert greet("World") == "Hello, World!"\nassert add(2, 3) == 5\nprint("All tests passed!")\n'),
    ]

    outputs = []
    for filename, content in steps:
        alpha.logger.tool_call("code", {"operation": "write_file", "filename": filename})
        result = await code_tool({"operation": "write_file", "filename": filename, "content": content})
        alpha.logger.tool_result("code", result)
        outputs.append(result)
        print(f"  Alpha wrote: {filename} ({result.get('size_bytes', 0)} bytes)")

    # Store on Filecoin
    store_result = await alpha.filecoin.store("alpha_task_output", {
        "files": [s[0] for s in steps],
        "status": "completed",
        "agent": alpha.name,
    })
    print(f"  Alpha stored on Filecoin: CID={store_result.get('cid', '?')[:30]}...")

    # Record completion onchain
    await alpha.erc8004.record_task_completed()
    alpha_rep = await alpha.erc8004.get_reputation()
    print(f"  Alpha reputation: {alpha_rep.get('reputation_score', '?')}")

    # ---- Phase 3: Beta evaluates Alpha's work ----
    print("\n" + "=" * 60)
    print("PHASE 3: BETA EVALUATES ALPHA")
    print("=" * 60)

    # Beta reviews Alpha's outputs
    eval_prompt = f"""Evaluate the following agent's work:
Agent: {alpha.name} (token_id: {alpha.token_id})
Task: Build a utility library
Outputs: {json.dumps(outputs)}
Files created: {[s[0] for s in steps]}

Please provide a quality evaluation and trust recommendation."""

    eval_response = beta.llm.complete_sync("You are an evaluator agent.", eval_prompt)
    evaluation = json.loads(eval_response)

    print(f"  Quality Score: {evaluation['evaluation']['quality_score']}/100")
    print(f"  Complete: {evaluation['evaluation']['completeness']}")
    print(f"  Recommendation: {evaluation['evaluation']['recommendation']}")
    print(f"  Trust Score: {evaluation['evaluation']['trust_score']}")

    # ---- Phase 4: Beta sets trust for Alpha onchain ----
    print("\n" + "=" * 60)
    print("PHASE 4: ONCHAIN TRUST UPDATE")
    print("=" * 60)

    trust_score = evaluation["evaluation"]["trust_score"]
    tx_hash = await beta.erc8004.set_trust(alpha.token_id, trust_score)
    print(f"  Beta set trust for Alpha: {trust_score}/100")
    print(f"  Transaction: {tx_hash[:32]}..." if tx_hash else "  Trust TX failed")

    # Verify trust on chain
    from web3 import Web3
    w3 = Web3(Web3.HTTPProvider("http://localhost:8545"))
    registry = w3.eth.contract(
        address=Web3.to_checksum_address(os.environ["ERC8004_REGISTRY_ADDRESS"]),
        abi=[{
            "inputs": [
                {"name": "fromAgent", "type": "uint256"},
                {"name": "toAgent", "type": "uint256"},
            ],
            "name": "trustScores",
            "outputs": [{"name": "", "type": "uint8"}],
            "stateMutability": "view",
            "type": "function",
        }],
    )
    onchain_trust = registry.functions.trustScores(beta.token_id, alpha.token_id).call()
    print(f"  Onchain trust (Beta->Alpha): {onchain_trust}")

    # ---- Phase 5: Summary ----
    print("\n" + "=" * 60)
    print("MULTI-AGENT DEMO SUMMARY")
    print("=" * 60)

    alpha_rep_final = await alpha.erc8004.get_reputation()
    beta_rep_final = await beta.erc8004.get_reputation()

    print(f"""
  Agent Alpha ({alpha.name}):
    Token ID: {alpha.token_id}
    Reputation: {alpha_rep_final.get('reputation_score', '?')}
    Tasks Completed: {alpha_rep_final.get('tasks_completed', '?')}

  Agent Beta ({beta.name}):
    Token ID: {beta.token_id}
    Reputation: {beta_rep_final.get('reputation_score', '?')}

  Trust Relationship:
    Beta -> Alpha: {onchain_trust}/100 (onchain verified)

  Artifacts:
    Alpha log: alpha_log.json ({len(alpha.logger.entries)} entries, chain valid: {alpha.logger.verify_chain()})
    Beta log:  beta_log.json ({len(beta.logger.entries)} entries, chain valid: {beta.logger.verify_chain()})
    """)

    # Save logs
    alpha.logger.save()
    beta.logger.save()

    print("ALL PHASES COMPLETE")


if __name__ == "__main__":
    asyncio.run(run_multi_agent_demo())
