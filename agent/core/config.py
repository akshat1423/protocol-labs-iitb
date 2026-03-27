"""AgentProof configuration loaded from environment variables."""

import os
from dataclasses import dataclass, field
from dotenv import load_dotenv

load_dotenv()


@dataclass
class AgentConfig:
    # Identity
    agent_name: str = os.getenv("AGENT_NAME", "AgentProof-Alpha")
    operator_private_key: str = os.getenv("OPERATOR_PRIVATE_KEY", "")

    # LLM
    anthropic_api_key: str = os.getenv("ANTHROPIC_API_KEY", "")
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    gemini_api_key: str = os.getenv("GEMINI_API_KEY", "")
    openrouter_api_key: str = os.getenv("OPENROUTER_API_KEY", "")
    llm_provider: str = os.getenv("LLM_PROVIDER", "openrouter")  # "openrouter", "gemini", "anthropic", or "openai"
    llm_model: str = os.getenv("LLM_MODEL", "openai/gpt-4.1-mini")

    # Blockchain
    sepolia_rpc_url: str = os.getenv("SEPOLIA_RPC_URL", "https://rpc.sepolia.org")
    filecoin_rpc_url: str = os.getenv("FILECOIN_CALIBRATION_RPC", "https://api.calibration.node.glif.io/rpc/v1")
    erc8004_registry_address: str = os.getenv("ERC8004_REGISTRY_ADDRESS", "")

    # Lit Protocol
    lit_vincent_api_key: str = os.getenv("LIT_VINCENT_API_KEY", "")

    # Storacha
    storacha_space_did: str = os.getenv("STORACHA_SPACE_DID", "")

    # Budget & Limits
    compute_budget_usd: float = float(os.getenv("COMPUTE_BUDGET_USD", "5.0"))
    max_llm_calls: int = int(os.getenv("MAX_LLM_CALLS", "100"))
    max_tool_calls: int = int(os.getenv("MAX_TOOL_CALLS", "50"))

    # Server
    dashboard_ws_port: int = int(os.getenv("DASHBOARD_WS_PORT", "8765"))


config = AgentConfig()
