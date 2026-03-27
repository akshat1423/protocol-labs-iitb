"""AgentProof entry point — starts the autonomous agent and dashboard server."""

from __future__ import annotations

import argparse
import asyncio
import sys


def main():
    parser = argparse.ArgumentParser(description="AgentProof — Verifiable Autonomous AI Agent")
    parser.add_argument("--task", type=str, help="Initial task for the agent")
    parser.add_argument("--headless", action="store_true", help="Run without dashboard server")
    args = parser.parse_args()

    print("""
    ╔═══════════════════════════════════════════════════╗
    ║          AgentProof — Autonomous Agent             ║
    ║     Verifiable AI with Onchain Identity             ║
    ╠═══════════════════════════════════════════════════╣
    ║  ERC-8004 Identity  │  Filecoin State              ║
    ║  Storacha Memory    │  Lit Protocol Wallet          ║
    ║  Hash-Chained Logs  │  Real-time Dashboard          ║
    ╚═══════════════════════════════════════════════════╝
    """)

    from .runner import run_full

    try:
        asyncio.run(run_full(task=args.task, headless=args.headless))
    except KeyboardInterrupt:
        print("\nAgent stopped by user.")
        sys.exit(0)


if __name__ == "__main__":
    main()
