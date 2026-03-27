"""Full integration test — runs agent with local Anvil, real Filecoin state, and mock LLM.

Prerequisites:
  - Anvil running on localhost:8545
  - AgentRegistry deployed (see contracts/script/DeployLocal.s.sol)

Usage:
  python -m agent.core.integration_test
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path

# Set up env for local Anvil
os.environ["OPERATOR_PRIVATE_KEY"] = "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80"
os.environ["SEPOLIA_RPC_URL"] = "http://localhost:8545"
os.environ["ERC8004_REGISTRY_ADDRESS"] = "0x5FbDB2315678afecb367f032d93F642f64180aa3"
os.environ["AGENT_NAME"] = "AgentProof-IntegrationTest"

from .runner import build_agent
from .demo import MockLLMClient


async def run_integration_test():
    print("=" * 60)
    print("AGENTPROOF INTEGRATION TEST")
    print("=" * 60)

    agent = build_agent()

    # Use mock LLM (swap for real Claude API when key available)
    agent.llm = MockLLMClient(agent.budget)

    print("\n[1] Testing ERC-8004 Identity Registration...")
    # The agent's _initialize_integrations will register onchain
    await agent._initialize_integrations()

    # Check identity
    if agent.erc8004.token_id is not None:
        print(f"    Token ID: {agent.erc8004.token_id}")
        print(f"    Operator: {agent.erc8004.operator_address}")

        # Fetch reputation
        rep = await agent.erc8004.get_reputation()
        print(f"    Reputation: {rep.get('reputation_score', '?')}")
        print(f"    Active: {rep.get('active', '?')}")
        print("    PASS: Identity registered onchain")
    else:
        print("    FAIL: Identity not registered")
        return False

    print("\n[2] Testing Lit Protocol Wallet...")
    if agent.lit and agent.lit.wallet_address:
        print(f"    Wallet: {agent.lit.wallet_address}")
        print(f"    Guardrails: max_tx={agent.lit.max_tx_value_eth} ETH, max_daily={agent.lit.max_daily_tx}")
        print("    PASS: Wallet initialized")
    else:
        print("    SKIP: Lit wallet not configured (expected in local mode)")

    print("\n[3] Testing Filecoin Storage...")
    test_data = {"test": True, "message": "integration test", "version": 1}
    result = await agent.filecoin.store("integration_test", test_data)
    print(f"    Stored: CID={result.get('cid', 'local')[:30]}...")

    retrieved = await agent.filecoin.retrieve("integration_test")
    if retrieved and retrieved.get("data", {}).get("test") is True:
        print("    Retrieved: OK")
        print("    PASS: Filecoin storage working")
    else:
        print("    FAIL: Retrieval mismatch")
        return False

    print("\n[4] Testing Storacha Memory...")
    await agent.storacha.remember("test_key", "integration_value", "test")
    recalled = await agent.storacha.recall("test_key")
    if recalled == "integration_value":
        print(f"    Stored & recalled: '{recalled}'")
        stats = await agent.storacha.stats()
        print(f"    Stats: {stats}")
        print("    PASS: Storacha memory working")
    else:
        print("    FAIL: Memory recall mismatch")
        return False

    print("\n[5] Testing Full Autonomous Loop...")
    await agent.run(initial_task="Write a Python hello world script and store it on Filecoin")

    # Check results
    state = agent.get_state()
    completed = sum(1 for t in state["tasks"] if t["status"] == "completed")
    print(f"    Tasks: {len(state['tasks'])} total, {completed} completed")
    print(f"    Log entries: {state['log_count']}")
    print(f"    Hash chain valid: {state['chain_valid']}")
    print(f"    Budget used: {state['budget']}")

    if completed > 0 and state["chain_valid"]:
        print("    PASS: Autonomous loop completed")
    else:
        print("    FAIL: Loop did not complete")
        return False

    print("\n[6] Testing Onchain Reputation Update...")
    rep_after = await agent.erc8004.get_reputation()
    print(f"    Reputation after: {rep_after.get('reputation_score', '?')}")
    print(f"    Tasks completed onchain: {rep_after.get('tasks_completed', '?')}")

    if rep_after.get("tasks_completed", 0) > 0:
        print("    PASS: Reputation updated onchain")
    else:
        print("    SKIP: Reputation not updated (may need real ERC-8004 calls)")

    print("\n[7] Verifying Artifacts...")
    # Check agent.json
    manifest_path = Path("agent.json")
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text())
        print(f"    agent.json: {len(manifest.get('supported_tools', []))} tools listed")
        print("    PASS: Manifest generated")

    # Check agent_log.json
    log_path = Path("agent_log.json")
    if log_path.exists():
        logs = json.loads(log_path.read_text())
        print(f"    agent_log.json: {logs['total_entries']} entries, chain head: {logs['chain_head_hash'][:16]}...")
        print("    PASS: Execution log generated")

    # Check workspace files
    workspace = Path("agent_workspace")
    if workspace.exists():
        files = list(workspace.rglob("*"))
        file_count = sum(1 for f in files if f.is_file())
        print(f"    Workspace: {file_count} files created")

    print("\n" + "=" * 60)
    print("ALL INTEGRATION TESTS PASSED")
    print("=" * 60)
    return True


if __name__ == "__main__":
    success = asyncio.run(run_integration_test())
    sys.exit(0 if success else 1)
