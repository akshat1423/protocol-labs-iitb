"""Demo mode — runs AgentProof with mock LLM for testing without API keys."""

from __future__ import annotations

import asyncio
import json
import time

from .agent import AgentProof, SYSTEM_PROMPT
from .models import BudgetTracker, Task
from .runner import build_agent


class MockLLMClient:
    """Mock LLM that returns structured responses for demo/testing."""

    def __init__(self, budget: BudgetTracker):
        self.budget = budget
        self._call_count = 0

    def complete_sync(self, system_prompt: str, user_message: str, temperature: float = 0.7) -> str:
        self._call_count += 1
        self.budget.record_llm_call(0.001)

        # Route based on what phase we're in
        if "identify a meaningful task" in user_message:
            return json.dumps({
                "title": "Build a Hello World smart contract",
                "description": "Create and test a simple Solidity smart contract that stores a greeting message",
                "source": "hackathon_challenge",
                "plan": [
                    "Write the Solidity smart contract code",
                    "Write a test file for the contract",
                    "Create a README documenting the contract",
                    "Store the contract code on Filecoin",
                    "Record task completion in agent memory",
                ]
            })

        if "Create a detailed execution plan" in user_message:
            return json.dumps([
                "Write the Solidity smart contract code using the code tool",
                "Write a test file for the contract",
                "Create documentation for the contract",
                "Store the artifacts on Filecoin for persistence",
                "Save completion status to agent memory via Storacha",
            ])

        if "Execute this step" in user_message:
            if "Solidity smart contract" in user_message and "test" not in user_message.lower():
                return json.dumps({
                    "reasoning": "Writing a simple Greeter smart contract in Solidity",
                    "tool": "code",
                    "params": {
                        "operation": "write_file",
                        "filename": "Greeter.sol",
                        "content": '// SPDX-License-Identifier: MIT\npragma solidity ^0.8.20;\n\ncontract Greeter {\n    string public greeting;\n\n    constructor(string memory _greeting) {\n        greeting = _greeting;\n    }\n\n    function setGreeting(string memory _greeting) public {\n        greeting = _greeting;\n    }\n\n    function greet() public view returns (string memory) {\n        return greeting;\n    }\n}\n'
                    },
                    "expected_output": "File written successfully"
                })
            elif "test" in user_message.lower():
                return json.dumps({
                    "reasoning": "Writing a test file for the Greeter contract",
                    "tool": "code",
                    "params": {
                        "operation": "write_file",
                        "filename": "Greeter.test.js",
                        "content": '// Test file for Greeter contract\nconst assert = require("assert");\n\ndescribe("Greeter", function() {\n  it("should return the greeting", function() {\n    assert.equal(true, true); // placeholder\n  });\n});\n'
                    },
                    "expected_output": "Test file written"
                })
            elif "documentation" in user_message.lower() or "README" in user_message:
                return json.dumps({
                    "reasoning": "Creating documentation for the contract",
                    "tool": "code",
                    "params": {
                        "operation": "write_file",
                        "filename": "CONTRACT_README.md",
                        "content": "# Greeter Contract\n\nA simple smart contract that stores and returns a greeting.\n\n## Functions\n- `greet()` - Returns the current greeting\n- `setGreeting(string)` - Updates the greeting\n"
                    },
                    "expected_output": "Documentation written"
                })
            elif "Filecoin" in user_message or "Store" in user_message:
                return json.dumps({
                    "reasoning": "Storing artifacts on Filecoin for decentralized persistence",
                    "tool": "filecoin",
                    "params": {
                        "operation": "store",
                        "key": "greeter_contract",
                        "data": {"contract": "Greeter.sol", "test": "Greeter.test.js", "status": "complete"}
                    },
                    "expected_output": "CID returned for stored data"
                })
            elif "memory" in user_message.lower() or "Storacha" in user_message:
                return json.dumps({
                    "reasoning": "Saving task completion to persistent memory",
                    "tool": "storacha",
                    "params": {
                        "operation": "remember",
                        "key": "greeter_task_complete",
                        "value": "Successfully built and documented Greeter contract",
                        "category": "completed_tasks"
                    },
                    "expected_output": "Memory stored"
                })

            # Default tool action
            return json.dumps({
                "reasoning": "Proceeding with the step",
                "tool": "none",
                "params": {},
                "expected_output": "Step completed"
            })

        if "Verify whether this task" in user_message:
            return json.dumps({
                "verified": True,
                "confidence": 0.92,
                "reasoning": "All planned steps executed successfully: contract written, tests created, documentation added, artifacts stored on Filecoin, and completion recorded in memory.",
                "issues": []
            })

        # Default response
        return json.dumps({"status": "ok", "message": "Acknowledged"})


async def run_demo():
    """Run AgentProof in demo mode with mock LLM."""
    print("""
    ╔═══════════════════════════════════════════════════╗
    ║          AgentProof — DEMO MODE                    ║
    ║     Running with mock LLM (no API keys needed)     ║
    ╠═══════════════════════════════════════════════════╣
    ║  Demonstrating: discover -> plan -> execute ->      ║
    ║  verify cycle with all integrations                 ║
    ╚═══════════════════════════════════════════════════╝
    """)

    agent = build_agent()

    # Replace LLM with mock
    agent.llm = MockLLMClient(agent.budget)

    # Run the agent
    await agent.run()

    # Print results
    print("\n" + "=" * 60)
    print("DEMO RESULTS")
    print("=" * 60)

    state = agent.get_state()
    print(f"\nAgent: {state['identity']['agent_name']}")
    print(f"Tools used: {state['identity']['supported_tools']}")
    print(f"Budget: {state['budget']}")
    print(f"Log entries: {state['log_count']}")
    print(f"Hash chain valid: {state['chain_valid']}")

    for task in state["tasks"]:
        print(f"\nTask: {task['title']}")
        print(f"  Status: {task['status']}")
        print(f"  Plan steps: {len(task['plan'])}")
        print(f"  Outputs: {len(task['outputs'])}")
        if task["error"]:
            print(f"  Error: {task['error']}")

    # Show log chain
    print(f"\nExecution log saved to: agent_log.json")
    print(f"Agent manifest saved to: agent.json")

    # Show stored files
    if agent.filecoin:
        items = await agent.filecoin.list_stored()
        print(f"\nFilecoin stored items: {len(items)}")
        for item in items:
            print(f"  - {item['key']} ({item['size_bytes']} bytes)")

    if agent.storacha:
        stats = await agent.storacha.stats()
        print(f"\nStoracha memory: {stats}")


if __name__ == "__main__":
    asyncio.run(run_demo())
