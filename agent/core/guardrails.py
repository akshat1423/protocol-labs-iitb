"""Safety guardrails for AgentProof — validates actions before execution."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .logger import ExecutionLogger
from .models import BudgetTracker


@dataclass
class GuardrailResult:
    allowed: bool
    reason: str = ""


class Guardrails:
    """Validates agent actions for safety before execution."""

    BLOCKED_OPERATIONS = [
        "rm -rf /",
        "DROP TABLE",
        "DROP DATABASE",
        "format c:",
        "sudo rm",
        "mkfs",
        "> /dev/sda",
    ]

    MAX_TRANSACTION_VALUE_ETH = 0.1  # Max 0.1 ETH per transaction
    MAX_FILE_WRITE_SIZE_KB = 500

    def __init__(self, budget: BudgetTracker, logger: ExecutionLogger):
        self.budget = budget
        self.logger = logger
        self._paused = False

    @property
    def is_paused(self) -> bool:
        return self._paused

    def pause(self):
        """Kill switch — pause all agent operations."""
        self._paused = True
        self.logger.safety("Agent paused via kill switch")

    def resume(self):
        self._paused = False
        self.logger.info("safety", "Agent resumed")

    def check_budget(self, estimated_cost: float = 0.01) -> GuardrailResult:
        if not self.budget.can_spend(estimated_cost):
            self.logger.guardrail(
                f"Budget exceeded: {self.budget.summary()}"
            )
            return GuardrailResult(False, "Compute budget exceeded")
        return GuardrailResult(True)

    def check_command(self, command: str) -> GuardrailResult:
        if self._paused:
            return GuardrailResult(False, "Agent is paused")

        for blocked in self.BLOCKED_OPERATIONS:
            if blocked.lower() in command.lower():
                self.logger.safety(
                    f"Blocked dangerous command: {command}",
                    data={"blocked_pattern": blocked},
                )
                return GuardrailResult(False, f"Dangerous operation detected: {blocked}")

        return GuardrailResult(True)

    def check_transaction(self, to: str, value_eth: float, data: str = "") -> GuardrailResult:
        if self._paused:
            return GuardrailResult(False, "Agent is paused")

        if value_eth > self.MAX_TRANSACTION_VALUE_ETH:
            self.logger.safety(
                f"Transaction value {value_eth} ETH exceeds limit {self.MAX_TRANSACTION_VALUE_ETH} ETH",
                data={"to": to, "value_eth": value_eth},
            )
            return GuardrailResult(False, f"Value exceeds max: {value_eth} > {self.MAX_TRANSACTION_VALUE_ETH} ETH")

        if not to or len(to) != 42 or not to.startswith("0x"):
            self.logger.safety(f"Invalid transaction recipient: {to}")
            return GuardrailResult(False, f"Invalid recipient address: {to}")

        return GuardrailResult(True)

    def check_file_write(self, path: str, content: str) -> GuardrailResult:
        if self._paused:
            return GuardrailResult(False, "Agent is paused")

        size_kb = len(content.encode()) / 1024
        if size_kb > self.MAX_FILE_WRITE_SIZE_KB:
            self.logger.guardrail(f"File write too large: {size_kb:.1f}KB > {self.MAX_FILE_WRITE_SIZE_KB}KB")
            return GuardrailResult(False, f"File too large: {size_kb:.1f}KB")

        dangerous_paths = ["/etc/", "/usr/", "/bin/", "/sbin/", "/root/"]
        for dp in dangerous_paths:
            if path.startswith(dp):
                self.logger.safety(f"Blocked write to system path: {path}")
                return GuardrailResult(False, f"Cannot write to system path: {path}")

        return GuardrailResult(True)

    def check_api_call(self, url: str) -> GuardrailResult:
        if self._paused:
            return GuardrailResult(False, "Agent is paused")
        return GuardrailResult(True)

    def validate_action(self, action_type: str, params: dict[str, Any]) -> GuardrailResult:
        """Universal action validator — routes to specific checks."""
        if self._paused:
            return GuardrailResult(False, "Agent is paused")

        budget_check = self.check_budget()
        if not budget_check.allowed:
            return budget_check

        validators = {
            "command": lambda p: self.check_command(p.get("command", "")),
            "transaction": lambda p: self.check_transaction(
                p.get("to", ""), p.get("value_eth", 0), p.get("data", "")
            ),
            "file_write": lambda p: self.check_file_write(p.get("path", ""), p.get("content", "")),
            "api_call": lambda p: self.check_api_call(p.get("url", "")),
        }

        validator = validators.get(action_type)
        if validator:
            return validator(params)

        return GuardrailResult(True)
