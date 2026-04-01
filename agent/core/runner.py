"""Unified runner — wires all integrations and tools into the agent."""

from __future__ import annotations

import asyncio

from .agent import AgentProof
from .agents import route_task, get_all_specs, AgentSpec
from .config import config
from .server import DashboardServer

from ..integrations.erc8004 import ERC8004Identity
from ..integrations.filecoin_storage import FilecoinStorage
from ..integrations.storacha_memory import StorachaMemory
from ..integrations.lit_wallet import LitWallet

from ..tools.github_tool import GitHubTool
from ..tools.code_tool import CodeTool
from ..tools.web_tool import WebTool
from ..tools.blockchain_tool import BlockchainTool


def build_agent(spec: AgentSpec | None = None) -> AgentProof:
    """Build a fully configured AgentProof instance with all integrations.

    If spec is provided, applies that agent's system prompt and restricts tools.
    """
    agent = AgentProof()

    # --- Attach integrations ---
    erc8004 = ERC8004Identity(agent.logger)
    agent.attach_erc8004(erc8004)

    filecoin = FilecoinStorage(agent.logger)
    agent.attach_filecoin(filecoin)

    storacha = StorachaMemory(agent.logger)
    agent.attach_storacha(storacha)

    lit = LitWallet(agent.logger)
    agent.attach_lit(lit)

    # --- Register tools ---
    github = GitHubTool()
    code = CodeTool()
    web = WebTool()
    blockchain = BlockchainTool()

    agent.register_tool("github", github)
    agent.register_tool("code", code)
    agent.register_tool("web", web)
    agent.register_tool("blockchain", blockchain)

    # Filecoin as a tool (store/retrieve)
    async def filecoin_tool(params):
        op = params.get("operation", "store")
        if op == "store":
            key = params.get("key", "data")
            data = params.get("data", {})
            # If LLM passes a filename, read that file and store its contents
            filename = params.get("filename")
            if filename:
                from pathlib import Path
                for prefix in ["agent_workspace/", "./agent_workspace/"]:
                    if filename.startswith(prefix):
                        filename = filename[len(prefix):]
                filepath = Path("./agent_workspace") / filename
                if filepath.exists():
                    data = {"filename": filename, "content": filepath.read_text()[:10000]}
                    key = key if key != "data" else filename
                else:
                    return {"error": f"File not found: {filename}"}
            return await filecoin.store(key, data)
        elif op == "retrieve":
            return await filecoin.retrieve(params.get("key", ""))
        elif op == "list":
            return await filecoin.list_stored()
        return {"error": f"Unknown filecoin operation: {op}"}

    agent.register_tool("filecoin", filecoin_tool)

    # Storacha as a tool (remember/recall)
    async def storacha_tool(params):
        op = params.get("operation", "remember")
        if op == "remember":
            await storacha.remember(params.get("key", ""), params.get("value", ""), params.get("category", "general"))
            return {"status": "remembered"}
        elif op == "recall":
            value = await storacha.recall(params.get("key", ""))
            return {"value": value}
        elif op == "context":
            return {"context": await storacha.get_context()}
        return {"error": f"Unknown storacha operation: {op}"}

    agent.register_tool("storacha", storacha_tool)

    # ERC-8004 as a tool (reputation/trust)
    async def identity_tool(params):
        op = params.get("operation", "get_reputation")
        if op == "get_reputation":
            return await erc8004.get_reputation()
        elif op == "set_trust":
            tx = await erc8004.set_trust(params.get("target_id", 0), params.get("score", 50))
            return {"tx_hash": tx}
        return {"error": f"Unknown identity operation: {op}"}

    agent.register_tool("identity", identity_tool)

    # Lit Protocol wallet as a tool
    async def wallet_tool(params):
        op = params.get("operation", "status")
        if op == "status":
            return lit.get_status()
        elif op == "balance":
            return await lit.get_balance(params.get("chain", "sepolia"))
        elif op == "sign_message":
            return await lit.sign_message(params.get("message", ""))
        elif op == "sign_transaction":
            return await lit.sign_transaction(params.get("transaction", {}))
        return {"error": f"Unknown wallet operation: {op}"}

    agent.register_tool("wallet", wallet_tool)

    # Apply spec: override system prompt, restrict to allowed tools, set agent_id
    if spec is not None:
        agent.system_prompt = spec.system_prompt
        agent.agent_id = spec.id
        agent.identity.agent_name = spec.name
        # Remove tools not in this agent's allowed list
        disallowed = [t for t in list(agent._tools.keys()) if t not in spec.tools]
        for t in disallowed:
            del agent._tools[t]
        agent.identity.supported_tools = [t for t in agent.identity.supported_tools if t in spec.tools]

    return agent


def build_agent_for_task(task: str) -> tuple[AgentProof, "AgentSpec"]:
    """Auto-select and build the right agent for a given task."""
    spec = route_task(task)
    agent = build_agent(spec=spec)
    return agent, spec


async def run_full(task: str | None = None, headless: bool = False):
    """Build and run the full agent with dashboard."""
    agent = build_agent()

    if headless:
        await agent.run(initial_task=task)
    else:
        server = DashboardServer(agent)
        # Run dashboard server and agent concurrently
        await asyncio.gather(
            server.start(),
            agent.run(initial_task=task),
        )
