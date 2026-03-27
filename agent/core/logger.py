"""Structured execution logger with cryptographic hash chain for verifiability."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from rich.console import Console

from .models import LogEntry, LogLevel

console = Console()


class ExecutionLogger:
    """Produces structured, hash-chained execution logs (agent_log.json)."""

    def __init__(self, output_path: str = "agent_log.json"):
        self.output_path = Path(output_path)
        self.entries: list[LogEntry] = []
        self._last_hash: str | None = None
        self._listeners: list = []  # WebSocket listeners for dashboard

    def log(
        self,
        level: LogLevel,
        phase: str,
        message: str,
        data: dict[str, Any] | None = None,
        task_id: str | None = None,
    ) -> LogEntry:
        entry = LogEntry(
            timestamp=time.time(),
            level=level,
            phase=phase,
            message=message,
            data=data or {},
            task_id=task_id,
            parent_hash=self._last_hash,
        )
        self.entries.append(entry)
        self._last_hash = entry.entry_hash
        self._print(entry)
        self._notify_listeners(entry)
        self.save()  # Write to disk after every entry for real-time dashboard
        return entry

    def info(self, phase: str, message: str, **kwargs):
        return self.log(LogLevel.INFO, phase, message, **kwargs)

    def decision(self, phase: str, message: str, **kwargs):
        return self.log(LogLevel.DECISION, phase, message, **kwargs)

    def tool_call(self, tool_name: str, params: dict, task_id: str | None = None):
        return self.log(
            LogLevel.TOOL_CALL,
            "execute",
            f"Calling tool: {tool_name}",
            data={"tool": tool_name, "params": params},
            task_id=task_id,
        )

    def tool_result(self, tool_name: str, result: Any, task_id: str | None = None):
        return self.log(
            LogLevel.TOOL_RESULT,
            "execute",
            f"Tool result: {tool_name}",
            data={"tool": tool_name, "result": str(result)[:500]},
            task_id=task_id,
        )

    def error(self, phase: str, message: str, **kwargs):
        return self.log(LogLevel.ERROR, phase, message, **kwargs)

    def guardrail(self, message: str, **kwargs):
        return self.log(LogLevel.GUARDRAIL, "safety", message, **kwargs)

    def safety(self, message: str, **kwargs):
        return self.log(LogLevel.SAFETY, "safety", message, **kwargs)

    def _print(self, entry: LogEntry):
        """Pretty-print to terminal using rich."""
        color_map = {
            LogLevel.INFO: "blue",
            LogLevel.DECISION: "yellow",
            LogLevel.TOOL_CALL: "cyan",
            LogLevel.TOOL_RESULT: "green",
            LogLevel.ERROR: "red",
            LogLevel.GUARDRAIL: "magenta",
            LogLevel.SAFETY: "red bold",
        }
        color = color_map.get(entry.level, "white")
        prefix = f"[{color}][{entry.level.value:12}][/{color}]"
        phase = f"[dim]{entry.phase:8}[/dim]"
        console.print(f"{prefix} {phase} {entry.message}")

    def _notify_listeners(self, entry: LogEntry):
        """Send log entry to WebSocket listeners (dashboard)."""
        for listener in self._listeners:
            try:
                listener(entry.to_dict())
            except Exception:
                pass

    def add_listener(self, callback):
        self._listeners.append(callback)

    def save(self):
        """Write all logs to agent_log.json."""
        output = {
            "agent": "AgentProof",
            "total_entries": len(self.entries),
            "chain_head_hash": self._last_hash,
            "entries": [e.to_dict() for e in self.entries],
        }
        self.output_path.write_text(json.dumps(output, indent=2))

    def get_recent(self, n: int = 50) -> list[dict]:
        return [e.to_dict() for e in self.entries[-n:]]

    def verify_chain(self) -> bool:
        """Verify the hash chain integrity of all log entries."""
        for i, entry in enumerate(self.entries):
            if i == 0:
                if entry.parent_hash is not None:
                    return False
            else:
                if entry.parent_hash != self.entries[i - 1].entry_hash:
                    return False
            expected = entry._compute_hash()
            if entry.entry_hash != expected:
                return False
        return True
