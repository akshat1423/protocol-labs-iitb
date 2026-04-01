"""Run AgentProof with real Gemini API.

Usage:
  # Set your key first:
  export GEMINI_API_KEY=your_key_here
  # Or edit agent/.env

  python -m agent.core.run_gemini
  python -m agent.core.run_gemini --task "Write a Python fibonacci function"
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys

# Load .env
from dotenv import load_dotenv
load_dotenv()


async def run(task: str | None = None):
    from .runner import build_agent, build_agent_for_task
    from .config import config

    # Verify API key
    has_key = (
        (config.llm_provider == "openrouter" and config.openrouter_api_key) or
        (config.llm_provider == "gemini" and config.gemini_api_key) or
        (config.llm_provider == "anthropic" and config.anthropic_api_key) or
        (config.llm_provider == "openai" and config.openai_api_key)
    )
    if not has_key:
        print(f"ERROR: No API key set for provider '{config.llm_provider}'!")
        print(f"  Set it in agent/.env")
        sys.exit(1)

    print(f"""
    ╔═══════════════════════════════════════════════════════╗
    ║          AgentProof — LIVE MODE                        ║
    ║     Provider: {config.llm_provider:<39} ║
    ║     Model: {config.llm_model:<42} ║
    ╠═══════════════════════════════════════════════════════╣
    ║  ERC-8004 Identity  │  Filecoin State                  ║
    ║  Storacha Memory    │  Lit Protocol Wallet              ║
    ║  Hash-Chained Logs  │  8 Autonomous Tools               ║
    ╚═══════════════════════════════════════════════════════╝
    """)

    import json as _json
    from pathlib import Path as _Path
    from .agents import route_task, get_all_specs
    from .runner import build_agent_for_task

    # Write agent registry for dashboard
    _Path("agent_registry.json").write_text(_json.dumps(get_all_specs(), indent=2))

    task_str = task or default_task
    selected_spec = route_task(task_str)
    print(f"  Routing to: {selected_spec.icon} {selected_spec.name} ({selected_spec.role})\n")
    agent, _ = build_agent_for_task(task_str)

    # Quick LLM test
    print("Testing connection...")
    test_response = agent.llm.complete_sync(
        "You are a helpful assistant.",
        "Respond with exactly: {\"status\": \"ok\"}",
    )
    print(f"  Gemini says: {test_response.strip()[:100]}")
    print("  Connection OK!\n")

    default_task = "Write a Python script that generates the first 20 Fibonacci numbers, save it to a file, then store the result on Filecoin"
    await agent.run(initial_task=task or default_task)

    # Print summary
    state = agent.get_state()
    print("\n" + "=" * 60)
    print("RESULTS")
    print("=" * 60)
    print(f"Tasks: {len(state['tasks'])}")
    for t in state["tasks"]:
        print(f"  [{t['status']}] {t['title']}")
        if t["plan"]:
            for i, step in enumerate(t["plan"]):
                print(f"    {i+1}. {step}")
    print(f"\nBudget: {state['budget']}")
    print(f"Log entries: {state['log_count']}")
    print(f"Chain valid: {state['chain_valid']}")


def main():
    parser = argparse.ArgumentParser(description="AgentProof with Gemini")
    parser.add_argument("--task", type=str, help="Task for the agent")
    args = parser.parse_args()

    try:
        asyncio.run(run(task=args.task))
    except KeyboardInterrupt:
        print("\nStopped.")


if __name__ == "__main__":
    main()
