"""ERC-8004 onchain identity integration for AgentProof."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from web3 import Web3
from web3.middleware import ExtraDataToPOAMiddleware

try:
    from ..core.config import config
    from ..core.logger import ExecutionLogger
except ImportError:
    from core.config import config  # type: ignore
    from core.logger import ExecutionLogger  # type: ignore

# Minimal ABI for AgentRegistry interactions
REGISTRY_ABI = [
    {
        "inputs": [
            {"name": "name", "type": "string"},
            {"name": "metadataURI", "type": "string"},
        ],
        "name": "registerAgent",
        "outputs": [{"name": "", "type": "uint256"}],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [{"name": "tokenId", "type": "uint256"}],
        "name": "recordTaskCompleted",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [{"name": "tokenId", "type": "uint256"}],
        "name": "recordTaskFailed",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [
            {"name": "fromAgent", "type": "uint256"},
            {"name": "toAgent", "type": "uint256"},
            {"name": "score", "type": "uint8"},
        ],
        "name": "setTrust",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [{"name": "tokenId", "type": "uint256"}],
        "name": "getAgent",
        "outputs": [
            {
                "components": [
                    {"name": "name", "type": "string"},
                    {"name": "operator", "type": "address"},
                    {"name": "metadataURI", "type": "string"},
                    {"name": "reputationScore", "type": "uint256"},
                    {"name": "tasksCompleted", "type": "uint256"},
                    {"name": "tasksFailed", "type": "uint256"},
                    {"name": "registeredAt", "type": "uint256"},
                    {"name": "active", "type": "bool"},
                ],
                "name": "",
                "type": "tuple",
            }
        ],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [
            {"name": "tokenId", "type": "uint256"},
            {"name": "minScore", "type": "uint256"},
        ],
        "name": "meetsReputationThreshold",
        "outputs": [{"name": "", "type": "bool"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [],
        "name": "totalAgents",
        "outputs": [{"name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function",
    },
]


class ERC8004Identity:
    """Manages agent's onchain identity via ERC-8004 registry."""

    def __init__(self, logger: ExecutionLogger):
        self.logger = logger
        self.w3 = Web3(Web3.HTTPProvider(config.sepolia_rpc_url))
        self.w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)

        self.account = self.w3.eth.account.from_key(config.operator_private_key) if config.operator_private_key else None
        self.registry = None
        self.token_id: int | None = None

        if config.erc8004_registry_address:
            self.registry = self.w3.eth.contract(
                address=Web3.to_checksum_address(config.erc8004_registry_address),
                abi=REGISTRY_ABI,
            )

    @property
    def operator_address(self) -> str:
        return self.account.address if self.account else ""

    async def register(self, agent_name: str, metadata_uri: str) -> dict[str, Any]:
        """Register agent identity onchain."""
        if not self.registry or not self.account:
            self.logger.error("erc8004", "Registry or account not configured")
            return {"error": "Not configured"}

        self.logger.info("erc8004", f"Registering agent: {agent_name}")

        try:
            tx = self.registry.functions.registerAgent(
                agent_name, metadata_uri
            ).build_transaction({
                "from": self.account.address,
                "nonce": self.w3.eth.get_transaction_count(self.account.address),
                "gas": 500000,
                "gasPrice": self.w3.eth.gas_price,
            })

            signed = self.account.sign_transaction(tx)
            tx_hash = self.w3.eth.send_raw_transaction(signed.raw_transaction)
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)

            # Parse token ID from logs
            self.token_id = self._parse_token_id(receipt)

            self.logger.info(
                "erc8004",
                f"Agent registered! Token ID: {self.token_id}, TX: {tx_hash.hex()}",
                data={"token_id": self.token_id, "tx_hash": tx_hash.hex()},
            )

            return {
                "token_id": self.token_id,
                "tx_hash": tx_hash.hex(),
                "operator": self.account.address,
            }

        except Exception as e:
            self.logger.error("erc8004", f"Registration failed: {e}")
            return {"error": str(e)}

    async def record_task_completed(self) -> str | None:
        """Record a completed task onchain (increases reputation)."""
        if not self.token_id:
            return None

        try:
            tx = self.registry.functions.recordTaskCompleted(
                self.token_id
            ).build_transaction({
                "from": self.account.address,
                "nonce": self.w3.eth.get_transaction_count(self.account.address),
                "gas": 100000,
                "gasPrice": self.w3.eth.gas_price,
            })
            signed = self.account.sign_transaction(tx)
            tx_hash = self.w3.eth.send_raw_transaction(signed.raw_transaction)
            self.w3.eth.wait_for_transaction_receipt(tx_hash)

            self.logger.info("erc8004", f"Task completion recorded: {tx_hash.hex()}")
            return tx_hash.hex()
        except Exception as e:
            self.logger.error("erc8004", f"Failed to record completion: {e}")
            return None

    async def record_task_failed(self) -> str | None:
        """Record a failed task onchain (decreases reputation)."""
        if not self.token_id:
            return None

        try:
            tx = self.registry.functions.recordTaskFailed(
                self.token_id
            ).build_transaction({
                "from": self.account.address,
                "nonce": self.w3.eth.get_transaction_count(self.account.address),
                "gas": 100000,
                "gasPrice": self.w3.eth.gas_price,
            })
            signed = self.account.sign_transaction(tx)
            tx_hash = self.w3.eth.send_raw_transaction(signed.raw_transaction)
            self.w3.eth.wait_for_transaction_receipt(tx_hash)

            self.logger.info("erc8004", f"Task failure recorded: {tx_hash.hex()}")
            return tx_hash.hex()
        except Exception as e:
            self.logger.error("erc8004", f"Failed to record failure: {e}")
            return None

    async def get_reputation(self) -> dict[str, Any]:
        """Get current agent reputation from chain."""
        if not self.token_id or not self.registry:
            return {"error": "Not registered"}

        try:
            info = self.registry.functions.getAgent(self.token_id).call()
            return {
                "name": info[0],
                "operator": info[1],
                "metadata_uri": info[2],
                "reputation_score": info[3],
                "tasks_completed": info[4],
                "tasks_failed": info[5],
                "registered_at": info[6],
                "active": info[7],
            }
        except Exception as e:
            return {"error": str(e)}

    async def set_trust(self, target_agent_id: int, score: int) -> str | None:
        """Set trust score for another agent."""
        if not self.token_id:
            return None

        try:
            tx = self.registry.functions.setTrust(
                self.token_id, target_agent_id, score
            ).build_transaction({
                "from": self.account.address,
                "nonce": self.w3.eth.get_transaction_count(self.account.address),
                "gas": 100000,
                "gasPrice": self.w3.eth.gas_price,
            })
            signed = self.account.sign_transaction(tx)
            tx_hash = self.w3.eth.send_raw_transaction(signed.raw_transaction)
            self.w3.eth.wait_for_transaction_receipt(tx_hash)

            self.logger.info("erc8004", f"Trust set for agent {target_agent_id}: {score}")
            return tx_hash.hex()
        except Exception as e:
            self.logger.error("erc8004", f"Failed to set trust: {e}")
            return None

    def _parse_token_id(self, receipt) -> int | None:
        """Parse the token ID from the registration transaction receipt."""
        # Look for Transfer event (ERC-721 mint)
        for log in receipt.logs:
            if len(log.topics) >= 4:
                # Transfer(from, to, tokenId) — tokenId is the 4th topic
                return int(log.topics[3].hex(), 16)
        return 0
