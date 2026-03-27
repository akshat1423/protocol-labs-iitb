"""Data models for AgentProof agent state, tasks, and logs."""

from __future__ import annotations

import hashlib
import json
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class TaskStatus(str, Enum):
    DISCOVERED = "discovered"
    PLANNING = "planning"
    EXECUTING = "executing"
    VERIFYING = "verifying"
    COMPLETED = "completed"
    FAILED = "failed"
    ABORTED = "aborted"


class LogLevel(str, Enum):
    INFO = "info"
    DECISION = "decision"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    ERROR = "error"
    GUARDRAIL = "guardrail"
    SAFETY = "safety"


@dataclass
class AgentIdentity:
    agent_name: str
    operator_wallet: str
    erc8004_token_id: str | None = None
    erc8004_tx_hash: str | None = None
    capabilities: list[str] = field(default_factory=list)
    supported_tools: list[str] = field(default_factory=list)
    compute_constraints: dict[str, Any] = field(default_factory=dict)

    def to_manifest(self) -> dict:
        """Generate agent.json manifest (DevSpot compatible)."""
        return {
            "agent_name": self.agent_name,
            "operator_wallet": self.operator_wallet,
            "erc8004_identity": self.erc8004_token_id,
            "erc8004_registration_tx": self.erc8004_tx_hash,
            "supported_tools": self.supported_tools,
            "supported_tech_stacks": ["python", "solidity", "javascript"],
            "compute_constraints": self.compute_constraints,
            "supported_task_categories": [
                "code_generation",
                "smart_contract_deployment",
                "data_analysis",
                "api_integration",
            ],
        }


@dataclass
class Task:
    task_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    title: str = ""
    description: str = ""
    source: str = ""  # Where the task was discovered
    status: TaskStatus = TaskStatus.DISCOVERED
    plan: list[str] = field(default_factory=list)
    outputs: list[dict[str, Any]] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    completed_at: float | None = None
    error: str | None = None

    def to_dict(self) -> dict:
        return {
            "task_id": self.task_id,
            "title": self.title,
            "description": self.description,
            "source": self.source,
            "status": self.status.value,
            "plan": self.plan,
            "outputs": self.outputs,
            "created_at": self.created_at,
            "completed_at": self.completed_at,
            "error": self.error,
        }


@dataclass
class LogEntry:
    timestamp: float = field(default_factory=time.time)
    level: LogLevel = LogLevel.INFO
    phase: str = ""  # discover, plan, execute, verify
    message: str = ""
    data: dict[str, Any] = field(default_factory=dict)
    task_id: str | None = None
    parent_hash: str | None = None
    entry_hash: str = ""

    def __post_init__(self):
        if not self.entry_hash:
            self.entry_hash = self._compute_hash()

    def _compute_hash(self) -> str:
        """Cryptographic hash of this log entry for verifiable chain."""
        content = json.dumps({
            "timestamp": self.timestamp,
            "level": self.level.value,
            "phase": self.phase,
            "message": self.message,
            "data": self.data,
            "task_id": self.task_id,
            "parent_hash": self.parent_hash,
        }, sort_keys=True)
        return hashlib.sha256(content.encode()).hexdigest()

    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp,
            "level": self.level.value,
            "phase": self.phase,
            "message": self.message,
            "data": self.data,
            "task_id": self.task_id,
            "parent_hash": self.parent_hash,
            "entry_hash": self.entry_hash,
        }


@dataclass
class BudgetTracker:
    max_usd: float = 5.0
    max_llm_calls: int = 100
    max_tool_calls: int = 50
    spent_usd: float = 0.0
    llm_calls_used: int = 0
    tool_calls_used: int = 0

    def can_spend(self, estimated_cost: float = 0.01) -> bool:
        return (
            self.spent_usd + estimated_cost <= self.max_usd
            and self.llm_calls_used < self.max_llm_calls
            and self.tool_calls_used < self.max_tool_calls
        )

    def record_llm_call(self, cost: float = 0.01):
        self.llm_calls_used += 1
        self.spent_usd += cost

    def record_tool_call(self, cost: float = 0.0):
        self.tool_calls_used += 1
        self.spent_usd += cost

    def summary(self) -> dict:
        return {
            "spent_usd": round(self.spent_usd, 4),
            "max_usd": self.max_usd,
            "llm_calls": f"{self.llm_calls_used}/{self.max_llm_calls}",
            "tool_calls": f"{self.tool_calls_used}/{self.max_tool_calls}",
            "budget_remaining_pct": round(
                (1 - self.spent_usd / self.max_usd) * 100, 1
            ) if self.max_usd > 0 else 0,
        }
