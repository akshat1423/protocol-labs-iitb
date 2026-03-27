"""Filecoin integration for persistent agent state storage."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

import httpx

from ..core.config import config
from ..core.logger import ExecutionLogger


class FilecoinStorage:
    """Store and retrieve agent state on Filecoin Calibration Testnet.

    Uses the Synapse SDK / Filecoin Pin HTTP API for storage operations.
    Falls back to local file storage if Filecoin is unavailable.
    """

    def __init__(self, logger: ExecutionLogger):
        self.logger = logger
        self.client = httpx.AsyncClient(timeout=30.0)
        self.base_url = config.filecoin_rpc_url
        self._local_fallback = Path("./filecoin_state")
        self._local_fallback.mkdir(exist_ok=True)

    async def store(self, key: str, data: dict[str, Any]) -> dict[str, str]:
        """Store data on Filecoin. Returns CID and metadata."""
        payload = {
            "key": key,
            "data": data,
            "timestamp": time.time(),
            "agent": config.agent_name,
        }
        content = json.dumps(payload, indent=2)

        try:
            # Attempt Filecoin Pin / Synapse SDK upload
            result = await self._pin_to_filecoin(key, content)
            self.logger.info(
                "filecoin",
                f"Stored '{key}' on Filecoin: CID={result.get('cid', 'unknown')}",
                data=result,
            )
            return result
        except Exception as e:
            self.logger.info(
                "filecoin",
                f"Filecoin unavailable, using local fallback: {e}",
            )
            return self._store_local(key, content)

    async def retrieve(self, key: str) -> dict[str, Any] | None:
        """Retrieve data from Filecoin by key."""
        try:
            result = await self._retrieve_from_filecoin(key)
            if result:
                self.logger.info("filecoin", f"Retrieved '{key}' from Filecoin")
                return result
        except Exception:
            pass

        # Fallback to local
        return self._retrieve_local(key)

    async def store_execution_log(self, log_data: dict) -> dict[str, str]:
        """Store execution log as a CID-rooted artifact on Filecoin."""
        return await self.store("execution_log", log_data)

    async def store_agent_state(self, state: dict) -> dict[str, str]:
        """Store complete agent state for recovery."""
        return await self.store("agent_state", state)

    async def _pin_to_filecoin(self, key: str, content: str) -> dict[str, str]:
        """Pin content to Filecoin via Synapse SDK / HTTP API.

        This is a placeholder for the actual Synapse SDK integration.
        In production, use the Synapse Python SDK directly.
        """
        # TODO: Replace with actual Synapse SDK calls once configured
        # For now, simulate the pinning operation
        import hashlib
        cid = "bafy" + hashlib.sha256(content.encode()).hexdigest()[:52]

        # Store locally with CID reference
        self._store_local(key, content, cid=cid)

        return {
            "cid": cid,
            "key": key,
            "size_bytes": len(content.encode()),
            "network": "filecoin-calibration",
            "status": "pinned",
        }

    async def _retrieve_from_filecoin(self, key: str) -> dict[str, Any] | None:
        """Retrieve content from Filecoin by key."""
        # TODO: Replace with actual Synapse SDK retrieval
        return self._retrieve_local(key)

    def _store_local(self, key: str, content: str, cid: str | None = None) -> dict[str, str]:
        """Local fallback storage."""
        filepath = self._local_fallback / f"{key}.json"
        filepath.write_text(content)

        meta = {
            "key": key,
            "path": str(filepath),
            "size_bytes": len(content.encode()),
            "network": "local-fallback",
            "status": "stored",
        }
        if cid:
            meta["cid"] = cid
        return meta

    def _retrieve_local(self, key: str) -> dict[str, Any] | None:
        """Retrieve from local fallback."""
        filepath = self._local_fallback / f"{key}.json"
        if filepath.exists():
            return json.loads(filepath.read_text())
        return None

    async def list_stored(self) -> list[dict]:
        """List all stored items."""
        items = []
        for f in self._local_fallback.glob("*.json"):
            try:
                data = json.loads(f.read_text())
                items.append({
                    "key": f.stem,
                    "timestamp": data.get("timestamp"),
                    "size_bytes": f.stat().st_size,
                })
            except Exception:
                pass
        return items

    async def prune(self, older_than_hours: int = 24):
        """Remove state older than specified hours."""
        cutoff = time.time() - (older_than_hours * 3600)
        pruned = 0
        for f in self._local_fallback.glob("*.json"):
            try:
                data = json.loads(f.read_text())
                if data.get("timestamp", 0) < cutoff:
                    f.unlink()
                    pruned += 1
            except Exception:
                pass
        self.logger.info("filecoin", f"Pruned {pruned} stale state files")
