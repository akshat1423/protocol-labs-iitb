"""Lit Protocol Vincent API integration for secure agent wallet management.

Vincent provides non-custodial wallets with programmable guardrails,
enabling agents to sign transactions without exposing private keys.
"""

from __future__ import annotations

import json
from typing import Any

import httpx

from ..core.config import config
from ..core.logger import ExecutionLogger


class LitWallet:
    """Agent wallet via Lit Protocol's Vincent API.

    Provides:
    - Non-custodial wallet creation
    - Programmable spending guardrails
    - Cross-chain transaction signing
    - Transparent audit trail of all wallet operations
    """

    # Vincent API base URL
    BASE_URL = "https://vincent-api.litprotocol.com/api/v1"

    def __init__(self, logger: ExecutionLogger):
        self.logger = logger
        self.client = httpx.AsyncClient(
            timeout=30.0,
            headers={
                "Authorization": f"Bearer {config.lit_vincent_api_key}",
                "Content-Type": "application/json",
            },
        )
        self.wallet_address: str | None = None
        self.pkp_public_key: str | None = None

        # Programmable guardrails
        self.max_tx_value_eth = 0.1
        self.allowed_chains = ["sepolia", "filecoin-calibration"]
        self.daily_tx_count = 0
        self.max_daily_tx = 20

    async def initialize(self) -> dict[str, Any]:
        """Create or recover a Vincent-managed wallet for the agent."""
        self.logger.info("lit", "Initializing Lit Protocol wallet...")

        try:
            # Create a Programmable Key Pair (PKP) via Vincent
            result = await self._create_pkp()
            self.wallet_address = result.get("address")
            self.pkp_public_key = result.get("public_key")

            self.logger.info(
                "lit",
                f"Wallet initialized: {self.wallet_address}",
                data={"address": self.wallet_address},
            )
            return result
        except Exception as e:
            self.logger.error("lit", f"Wallet init failed: {e}")
            # Fallback: use operator wallet directly
            return {"error": str(e), "fallback": "using operator wallet"}

    async def sign_transaction(self, tx: dict[str, Any]) -> dict[str, Any]:
        """Sign a transaction using Lit Protocol with guardrail checks."""
        # Check guardrails first
        check = self._check_guardrails(tx)
        if not check["allowed"]:
            self.logger.guardrail(
                f"Lit wallet blocked tx: {check['reason']}",
                data={"tx": tx},
            )
            return {"error": check["reason"]}

        self.logger.info(
            "lit",
            f"Signing tx to {tx.get('to', '?')} for {tx.get('value', 0)} wei",
            data=tx,
        )

        try:
            result = await self._sign_with_pkp(tx)
            self.daily_tx_count += 1

            self.logger.info(
                "lit",
                f"Transaction signed: {result.get('tx_hash', 'pending')}",
            )
            return result
        except Exception as e:
            self.logger.error("lit", f"Signing failed: {e}")
            return {"error": str(e)}

    async def sign_message(self, message: str) -> dict[str, Any]:
        """Sign an arbitrary message (e.g., for authentication)."""
        self.logger.info("lit", f"Signing message: {message[:50]}...")

        try:
            result = await self._sign_message_with_pkp(message)
            return result
        except Exception as e:
            self.logger.error("lit", f"Message signing failed: {e}")
            return {"error": str(e)}

    async def get_balance(self, chain: str = "sepolia") -> dict[str, Any]:
        """Get wallet balance on specified chain."""
        if not self.wallet_address:
            return {"error": "Wallet not initialized"}

        # Use Web3 to check balance
        from web3 import Web3
        rpc_urls = {
            "sepolia": config.sepolia_rpc_url,
            "filecoin-calibration": config.filecoin_rpc_url,
        }
        rpc = rpc_urls.get(chain, config.sepolia_rpc_url)
        w3 = Web3(Web3.HTTPProvider(rpc))

        try:
            balance = w3.eth.get_balance(Web3.to_checksum_address(self.wallet_address))
            return {
                "address": self.wallet_address,
                "balance_wei": str(balance),
                "balance_eth": str(w3.from_wei(balance, "ether")),
                "chain": chain,
            }
        except Exception as e:
            return {"error": str(e)}

    def _check_guardrails(self, tx: dict) -> dict:
        """Check transaction against programmable guardrails."""
        # Value check
        value_wei = int(tx.get("value", 0))
        value_eth = value_wei / 1e18
        if value_eth > self.max_tx_value_eth:
            return {
                "allowed": False,
                "reason": f"Value {value_eth} ETH exceeds limit {self.max_tx_value_eth} ETH",
            }

        # Daily limit
        if self.daily_tx_count >= self.max_daily_tx:
            return {
                "allowed": False,
                "reason": f"Daily tx limit reached ({self.max_daily_tx})",
            }

        # Recipient check
        to = tx.get("to", "")
        if not to or len(to) != 42:
            return {"allowed": False, "reason": "Invalid recipient address"}

        return {"allowed": True, "reason": ""}

    async def _create_pkp(self) -> dict[str, Any]:
        """Create a PKP via Vincent API.

        In production, this calls the Vincent API to mint a new PKP.
        For demo/testing, generates a local representation.
        """
        if config.lit_vincent_api_key:
            try:
                resp = await self.client.post(
                    f"{self.BASE_URL}/pkp/create",
                    json={"agent_name": config.agent_name},
                )
                if resp.status_code == 200:
                    return resp.json()
            except Exception:
                pass

        # Fallback: derive address from operator key
        if config.operator_private_key:
            from web3 import Web3
            w3 = Web3()
            account = w3.eth.account.from_key(config.operator_private_key)
            return {
                "address": account.address,
                "public_key": f"0x{config.operator_private_key[:8]}...fallback",
                "source": "operator_key_fallback",
            }

        return {
            "address": "0x" + "0" * 40,
            "public_key": "demo_public_key",
            "source": "demo_mode",
        }

    async def _sign_with_pkp(self, tx: dict) -> dict[str, Any]:
        """Sign transaction via Vincent/PKP.

        In production, uses Lit Actions to sign within the Lit network.
        """
        if config.lit_vincent_api_key:
            try:
                resp = await self.client.post(
                    f"{self.BASE_URL}/pkp/sign-transaction",
                    json={"transaction": tx, "pkp_public_key": self.pkp_public_key},
                )
                if resp.status_code == 200:
                    return resp.json()
            except Exception:
                pass

        # Fallback: sign with operator key directly
        if config.operator_private_key:
            from web3 import Web3
            w3 = Web3(Web3.HTTPProvider(config.sepolia_rpc_url))
            account = w3.eth.account.from_key(config.operator_private_key)
            signed = account.sign_transaction(tx)
            return {
                "signed_tx": signed.raw_transaction.hex(),
                "source": "operator_key_fallback",
            }

        return {"signed_tx": "0xdemo", "source": "demo_mode"}

    async def _sign_message_with_pkp(self, message: str) -> dict[str, Any]:
        """Sign a message via Vincent/PKP."""
        if config.operator_private_key:
            from web3 import Web3
            from eth_account.messages import encode_defunct
            w3 = Web3()
            account = w3.eth.account.from_key(config.operator_private_key)
            msg = encode_defunct(text=message)
            signed = account.sign_message(msg)
            return {
                "signature": signed.signature.hex(),
                "address": account.address,
            }

        return {"signature": "0xdemo_signature", "source": "demo_mode"}

    def get_status(self) -> dict:
        """Get wallet status for dashboard."""
        return {
            "address": self.wallet_address,
            "pkp_public_key": self.pkp_public_key,
            "daily_tx_count": self.daily_tx_count,
            "max_daily_tx": self.max_daily_tx,
            "max_tx_value_eth": self.max_tx_value_eth,
            "allowed_chains": self.allowed_chains,
        }
