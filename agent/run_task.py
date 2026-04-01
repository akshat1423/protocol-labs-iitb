"""Standalone entry point for running an agent task.

Called as a subprocess by api.py:
    python run_task.py <task>
(run with cwd=agent/)
"""
from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

# Ensure agent/ dir is on path for absolute imports
sys.path.insert(0, str(Path(__file__).parent))

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent / ".env")
except Exception:
    pass


async def main(task: str):
    from core.runner import build_agent_for_task
    from core.agents import get_all_specs

    Path("agent_registry.json").write_text(json.dumps(get_all_specs(), indent=2))

    agent, spec = build_agent_for_task(task)
    await agent.run(initial_task=task)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python run_task.py <task>", file=sys.stderr)
        sys.exit(1)
    task = " ".join(sys.argv[1:])
    asyncio.run(main(task))
