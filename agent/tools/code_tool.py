"""Code generation tool — allows agent to write and execute code."""

from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path
from typing import Any


class CodeTool:
    """Agent tool for code generation, file writing, and execution."""

    WORKSPACE = Path("./agent_workspace")

    def __init__(self):
        self.WORKSPACE.mkdir(exist_ok=True)

    async def __call__(self, params: dict[str, Any]) -> dict[str, Any]:
        operation = params.get("operation", "")
        handlers = {
            "write_file": self.write_file,
            "read_file": self.read_file,
            "run_command": self.run_command,
            "list_files": self.list_files,
        }
        handler = handlers.get(operation)
        if not handler:
            return {"error": f"Unknown operation: {operation}"}
        return await handler(params)

    def _clean_filename(self, filename: str) -> str:
        """Strip workspace prefix if LLM accidentally includes it."""
        for prefix in ["agent_workspace/", "./agent_workspace/", "agent_workspace\\"]:
            if filename.startswith(prefix):
                filename = filename[len(prefix):]
        return filename

    def _strip_json_tail(self, content: str) -> str:
        """Remove JSON metadata the LLM sometimes appends after code content."""
        # Common patterns: "},"expected_output":... or "},"status":...
        import re
        # If content ends with a JSON fragment like "},"key":"value"...}
        # find the last clean line and truncate there
        match = re.search(r'\n?"?\}\s*,\s*"(expected_output|status|result|output)"', content)
        if match:
            content = content[:match.start()]
        return content.rstrip()

    async def write_file(self, params: dict) -> dict:
        filename = self._clean_filename(params.get("filename", "output.txt"))
        content = self._strip_json_tail(params.get("content", ""))
        filepath = self.WORKSPACE / filename
        filepath.parent.mkdir(parents=True, exist_ok=True)
        filepath.write_text(content)
        return {
            "path": str(filepath),
            "size_bytes": len(content.encode()),
            "status": "written",
        }

    async def read_file(self, params: dict) -> dict:
        filename = self._clean_filename(params.get("filename", ""))
        filepath = self.WORKSPACE / filename
        if not filepath.exists():
            return {"error": f"File not found: {filename}"}
        content = filepath.read_text()
        return {"content": content[:5000], "size_bytes": len(content.encode())}

    async def run_command(self, params: dict) -> dict:
        command = params.get("command", "")
        timeout = params.get("timeout", 30)

        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=str(self.WORKSPACE),
            )
            return {
                "stdout": result.stdout[:3000],
                "stderr": result.stderr[:1000],
                "returncode": result.returncode,
            }
        except subprocess.TimeoutExpired:
            return {"error": "Command timed out", "timeout": timeout}
        except Exception as e:
            return {"error": str(e)}

    async def list_files(self, params: dict) -> dict:
        pattern = params.get("pattern", "*")
        files = list(self.WORKSPACE.rglob(pattern))
        return {
            "files": [
                {"path": str(f.relative_to(self.WORKSPACE)), "size": f.stat().st_size}
                for f in files[:50]
                if f.is_file()
            ]
        }
