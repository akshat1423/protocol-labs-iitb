"""Storacha integration for persistent agent memory across sessions."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

import httpx

from ..core.config import config
from ..core.logger import ExecutionLogger


class StorachaMemory:
    """Persistent agent memory using Storacha decentralized storage.

    Stores conversation history, learned preferences, and agent knowledge
    that persists across restarts and devices.
    """

    def __init__(self, logger: ExecutionLogger):
        self.logger = logger
        self.client = httpx.AsyncClient(timeout=30.0)
        self._local_memory = Path("./storacha_memory")
        self._local_memory.mkdir(exist_ok=True)
        self.memories: dict[str, Any] = {}

    async def initialize(self):
        """Load memories from previous sessions."""
        self.logger.info("storacha", "Loading agent memory...")

        # Try to retrieve from Storacha
        try:
            stored = await self._retrieve_all()
            if stored:
                self.memories = stored
                self.logger.info(
                    "storacha",
                    f"Recovered {len(self.memories)} memory entries",
                )
                return
        except Exception as e:
            self.logger.info("storacha", f"Storacha unavailable: {e}")

        # Fallback: load from local
        self._load_local()
        self.logger.info("storacha", f"Loaded {len(self.memories)} memories from local")

    async def remember(self, key: str, value: Any, category: str = "general"):
        """Store a memory entry."""
        entry = {
            "value": value,
            "category": category,
            "stored_at": time.time(),
            "access_count": 0,
        }
        self.memories[key] = entry
        await self._persist()
        self.logger.info("storacha", f"Stored memory: {key} ({category})")

    async def recall(self, key: str) -> Any | None:
        """Retrieve a specific memory."""
        entry = self.memories.get(key)
        if entry:
            entry["access_count"] += 1
            return entry["value"]
        return None

    async def recall_category(self, category: str) -> dict[str, Any]:
        """Retrieve all memories in a category."""
        return {
            k: v["value"]
            for k, v in self.memories.items()
            if v.get("category") == category
        }

    async def forget(self, key: str):
        """Remove a memory entry."""
        if key in self.memories:
            del self.memories[key]
            await self._persist()

    async def remember_conversation(self, task_id: str, messages: list[dict]):
        """Store conversation history for a task."""
        await self.remember(
            f"conversation:{task_id}",
            messages,
            category="conversations",
        )

    async def remember_preference(self, key: str, value: Any):
        """Store a learned preference."""
        await self.remember(f"pref:{key}", value, category="preferences")

    async def get_context(self, max_entries: int = 10) -> str:
        """Get recent memory context for LLM prompts."""
        recent = sorted(
            self.memories.items(),
            key=lambda x: x[1].get("stored_at", 0),
            reverse=True,
        )[:max_entries]

        if not recent:
            return "No prior memories."

        lines = []
        for key, entry in recent:
            lines.append(f"- {key}: {json.dumps(entry['value'])[:200]}")
        return "\n".join(lines)

    async def _persist(self):
        """Save memories to both Storacha and local fallback."""
        content = json.dumps(self.memories, indent=2, default=str)

        # Save locally always
        (self._local_memory / "memories.json").write_text(content)

        # Try Storacha
        try:
            await self._upload_to_storacha(content)
        except Exception:
            pass

    async def _upload_to_storacha(self, content: str):
        """Upload memory blob to Storacha via w3 CLI."""
        import asyncio
        import tempfile
        import os

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write(content)
            tmp_path = f.name

        try:
            env = {k: v for k, v in os.environ.items() if k != "W3_PRINCIPAL"}
            proc = await asyncio.create_subprocess_exec(
                "w3", "up", "--no-wrap", tmp_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env,
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=30)
            output = stdout.decode() + stderr.decode()

            # Parse CID from output like: ⁂ https://w3s.link/ipfs/bafy...
            cid = None
            for line in output.splitlines():
                if "ipfs/" in line:
                    cid = line.strip().split("ipfs/")[-1].strip()
                    break

            if cid:
                self.logger.info("storacha", f"Memory synced: CID={cid}")
            else:
                self.logger.info("storacha", f"Upload output: {output[:200]}")
        except Exception as e:
            self.logger.info("storacha", f"Upload failed: {e}")
        finally:
            os.unlink(tmp_path)

    async def _retrieve_all(self) -> dict[str, Any] | None:
        """Retrieve all memories from Storacha."""
        # Local cache is source of truth; Storacha is write-only backup
        return None

    def _load_local(self):
        """Load memories from local fallback."""
        filepath = self._local_memory / "memories.json"
        if filepath.exists():
            try:
                self.memories = json.loads(filepath.read_text())
            except json.JSONDecodeError:
                self.memories = {}

    async def stats(self) -> dict:
        """Memory usage statistics."""
        categories = {}
        for entry in self.memories.values():
            cat = entry.get("category", "unknown")
            categories[cat] = categories.get(cat, 0) + 1

        return {
            "total_entries": len(self.memories),
            "categories": categories,
            "size_bytes": len(json.dumps(self.memories).encode()),
        }
