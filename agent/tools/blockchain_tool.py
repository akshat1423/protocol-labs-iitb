"""Blockchain tool — allows agent to perform onchain transactions."""

from __future__ import annotations

from typing import Any

from web3 import Web3

try:
    from ..core.config import config
except ImportError:
    from core.config import config  # type: ignore


class BlockchainTool:
    """Agent tool for reading/writing to Ethereum and Filecoin chains."""

    def __init__(self):
        self.w3_sepolia = Web3(Web3.HTTPProvider(config.sepolia_rpc_url))
        self.w3_filecoin = Web3(Web3.HTTPProvider(config.filecoin_rpc_url))
        self.account = (
            self.w3_sepolia.eth.account.from_key(config.operator_private_key)
            if config.operator_private_key
            else None
        )

    async def __call__(self, params: dict[str, Any]) -> dict[str, Any]:
        operation = params.get("operation", "")
        handlers = {
            "get_balance": self.get_balance,
            "get_block": self.get_block,
            "send_transaction": self.send_transaction,
            "read_contract": self.read_contract,
            "get_tx_receipt": self.get_tx_receipt,
            "chain_info": self.chain_info,
        }
        handler = handlers.get(operation)
        if not handler:
            return {"error": f"Unknown operation: {operation}"}
        return await handler(params)

    async def get_balance(self, params: dict) -> dict:
        address = params.get("address", self.account.address if self.account else "")
        chain = params.get("chain", "sepolia")
        w3 = self.w3_sepolia if chain == "sepolia" else self.w3_filecoin

        try:
            balance_wei = w3.eth.get_balance(Web3.to_checksum_address(address))
            balance_eth = w3.from_wei(balance_wei, "ether")
            return {
                "address": address,
                "balance_wei": str(balance_wei),
                "balance_eth": str(balance_eth),
                "chain": chain,
            }
        except Exception as e:
            return {"error": str(e)}

    async def get_block(self, params: dict) -> dict:
        chain = params.get("chain", "sepolia")
        block_id = params.get("block", "latest")
        w3 = self.w3_sepolia if chain == "sepolia" else self.w3_filecoin

        try:
            block = w3.eth.get_block(block_id)
            return {
                "number": block.number,
                "hash": block.hash.hex(),
                "timestamp": block.timestamp,
                "transactions": len(block.transactions),
                "gas_used": block.gasUsed,
            }
        except Exception as e:
            return {"error": str(e)}

    async def send_transaction(self, params: dict) -> dict:
        if not self.account:
            return {"error": "No operator wallet configured"}

        to = params.get("to", "")
        value_eth = float(params.get("value_eth", 0))
        data = params.get("data", "0x")

        try:
            tx = {
                "from": self.account.address,
                "to": Web3.to_checksum_address(to),
                "value": self.w3_sepolia.to_wei(value_eth, "ether"),
                "nonce": self.w3_sepolia.eth.get_transaction_count(self.account.address),
                "gas": int(params.get("gas", 21000)),
                "gasPrice": self.w3_sepolia.eth.gas_price,
            }
            if data != "0x":
                tx["data"] = data

            signed = self.account.sign_transaction(tx)
            tx_hash = self.w3_sepolia.eth.send_raw_transaction(signed.raw_transaction)
            receipt = self.w3_sepolia.eth.wait_for_transaction_receipt(tx_hash, timeout=60)

            return {
                "tx_hash": tx_hash.hex(),
                "status": receipt.status,
                "block_number": receipt.blockNumber,
                "gas_used": receipt.gasUsed,
            }
        except Exception as e:
            return {"error": str(e)}

    async def read_contract(self, params: dict) -> dict:
        """Read from a contract (view/pure function call)."""
        address = params.get("address", "")
        abi = params.get("abi", [])
        function_name = params.get("function", "")
        args = params.get("args", [])

        try:
            contract = self.w3_sepolia.eth.contract(
                address=Web3.to_checksum_address(address),
                abi=abi,
            )
            result = contract.functions[function_name](*args).call()
            return {"result": str(result)}
        except Exception as e:
            return {"error": str(e)}

    async def get_tx_receipt(self, params: dict) -> dict:
        tx_hash = params.get("tx_hash", "")
        try:
            receipt = self.w3_sepolia.eth.get_transaction_receipt(tx_hash)
            return {
                "status": receipt.status,
                "block_number": receipt.blockNumber,
                "gas_used": receipt.gasUsed,
                "logs": len(receipt.logs),
            }
        except Exception as e:
            return {"error": str(e)}

    async def chain_info(self, params: dict) -> dict:
        chain = params.get("chain", "sepolia")
        w3 = self.w3_sepolia if chain == "sepolia" else self.w3_filecoin

        try:
            return {
                "chain": chain,
                "chain_id": w3.eth.chain_id,
                "block_number": w3.eth.block_number,
                "gas_price_gwei": str(w3.from_wei(w3.eth.gas_price, "gwei")),
                "connected": w3.is_connected(),
            }
        except Exception as e:
            return {"error": str(e)}
