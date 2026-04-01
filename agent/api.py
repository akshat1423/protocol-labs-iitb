"""FastAPI server for AgentProof — exposes agent state and task execution as HTTP endpoints.

This replaces the local file-reading approach so the dashboard can talk to the
agent over HTTP when deployed on Railway (or any cloud platform).
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

# Ensure the agent directory is on the path so `core.*` imports work on Railway
sys.path.insert(0, str(Path(__file__).parent))

# Load .env if present (local dev)
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent / ".env")
except Exception:
    pass

from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(title="AgentProof API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── In-memory state (persisted to disk as well) ───────────────────────────────

_agent_running = False
_agent_task: asyncio.Task | None = None
_current_task_title: str = ""


# ── Helpers ───────────────────────────────────────────────────────────────────

def _read_json(path: str) -> Any:
    p = Path(path)
    if p.exists():
        try:
            return json.loads(p.read_text())
        except Exception:
            return None
    return None


def _read_log() -> dict:
    raw = _read_json("agent_log.json")
    if not raw:
        return {"total_entries": 0, "chain_head_hash": "", "recent_entries": []}
    return {
        "total_entries": raw.get("total_entries", 0),
        "chain_head_hash": raw.get("chain_head_hash", ""),
        "recent_entries": (raw.get("entries") or [])[-200:],
    }


def _read_manifest() -> dict | None:
    return _read_json("agent.json")


def _read_filecoin() -> list[str]:
    d = Path("filecoin_state")
    if d.exists():
        return [f.name for f in d.glob("*.json")]
    return []


def _read_memory() -> dict | None:
    raw = _read_json("storacha_memory/memories.json")
    if not raw:
        return None
    categories: dict[str, int] = {}
    for v in raw.values():
        cat = v.get("category", "unknown") if isinstance(v, dict) else "unknown"
        categories[cat] = categories.get(cat, 0) + 1
    return {"total_entries": len(raw), "categories": categories}


def _read_workspace() -> list[dict]:
    d = Path("agent_workspace")
    if not d.exists():
        return []
    files = []
    for f in d.iterdir():
        if f.is_file() and not f.name.startswith("."):
            try:
                content = f.read_text(errors="replace")
                files.append({"name": f.name, "content": content[:5000], "size": len(content)})
            except Exception:
                files.append({"name": f.name, "content": "", "size": 0})
    return files


def _read_registry() -> list | None:
    return _read_json("agent_registry.json")


# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "ok", "running": _agent_running, "timestamp": time.time()}


@app.get("/state")
def get_state():
    """Full agent state — dashboard polls this."""
    return {
        "manifest": _read_manifest(),
        "logs": _read_log(),
        "filecoin": {"items": _read_filecoin()},
        "memory": _read_memory(),
        "workspace": {"files": _read_workspace()},
        "agentRegistry": _read_registry(),
        "running": _agent_running,
        "timestamp": time.time(),
    }


@app.get("/running")
def get_running():
    return {"running": _agent_running}


class RunRequest(BaseModel):
    task: str


@app.post("/run")
async def run_agent(req: RunRequest, background_tasks: BackgroundTasks):
    global _agent_running, _current_task_title

    if _agent_running:
        raise HTTPException(status_code=409, detail="Agent is already running")

    if not req.task or not req.task.strip():
        raise HTTPException(status_code=400, detail="Missing task")

    _current_task_title = req.task
    background_tasks.add_task(_run_agent_task, req.task)
    return {"status": "started", "task": req.task}


async def _run_agent_task(task: str):
    global _agent_running
    _agent_running = True
    try:
        # Clean previous workspace
        import shutil
        for p in ["agent_log.json", "filecoin_state", "storacha_memory", "agent_workspace"]:
            path = Path(p)
            if path.exists():
                if path.is_dir():
                    shutil.rmtree(path, ignore_errors=True)
                else:
                    path.unlink(missing_ok=True)

        # Run agent as subprocess to avoid relative import issues
        agent_dir = Path(__file__).parent
        proc = await asyncio.create_subprocess_exec(
            sys.executable, str(agent_dir / "run_task.py"), task,
            cwd=str(agent_dir),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
        # Stream output to our stdout so Railway logs show agent output
        assert proc.stdout is not None
        async for line in proc.stdout:
            print(line.decode(errors="replace"), end="", flush=True)
        await proc.wait()
        if proc.returncode != 0:
            print(f"Agent subprocess exited with code {proc.returncode}")
    except Exception as e:
        print(f"Agent error: {e}")
    finally:
        _agent_running = False


@app.post("/stop")
def stop_agent():
    global _agent_running
    _agent_running = False
    return {"status": "stopped"}


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("api:app", host="0.0.0.0", port=port, reload=False)
