"""WebSocket server for real-time dashboard communication."""

from __future__ import annotations

import asyncio
import json
from typing import Any

import websockets
from websockets.server import serve

from .agent import AgentProof
from .config import config


class DashboardServer:
    """WebSocket server that streams agent state to the dashboard."""

    def __init__(self, agent: AgentProof):
        self.agent = agent
        self.clients: set = set()

    async def handler(self, websocket):
        self.clients.add(websocket)
        try:
            # Send initial state
            await websocket.send(json.dumps({
                "type": "state",
                "data": self.agent.get_state(),
            }))

            # Send recent logs
            await websocket.send(json.dumps({
                "type": "logs",
                "data": self.agent.logger.get_recent(100),
            }))

            # Listen for commands from dashboard
            async for message in websocket:
                await self._handle_command(message, websocket)
        except websockets.exceptions.ConnectionClosed:
            pass
        finally:
            self.clients.discard(websocket)

    async def _handle_command(self, message: str, websocket):
        """Handle commands from the dashboard."""
        try:
            cmd = json.loads(message)
            action = cmd.get("action")

            if action == "pause":
                self.agent.guardrails.pause()
                await self.broadcast({"type": "status", "data": {"paused": True}})

            elif action == "resume":
                self.agent.guardrails.resume()
                await self.broadcast({"type": "status", "data": {"paused": False}})

            elif action == "get_state":
                await websocket.send(json.dumps({
                    "type": "state",
                    "data": self.agent.get_state(),
                }))

            elif action == "add_task":
                from .models import Task
                task = Task(
                    title=cmd.get("title", "Dashboard Task"),
                    description=cmd.get("description", ""),
                    source="dashboard",
                )
                self.agent.tasks.append(task)
                await self.broadcast({"type": "task_added", "data": task.to_dict()})

        except json.JSONDecodeError:
            pass

    async def broadcast(self, message: dict):
        """Send a message to all connected dashboard clients."""
        if self.clients:
            data = json.dumps(message)
            await asyncio.gather(
                *[client.send(data) for client in self.clients],
                return_exceptions=True,
            )

    def setup_log_streaming(self):
        """Connect logger to broadcast log entries to dashboard."""
        def on_log(entry: dict):
            asyncio.create_task(self.broadcast({
                "type": "log",
                "data": entry,
            }))
        self.agent.logger.add_listener(on_log)

    async def start(self):
        """Start the WebSocket server."""
        self.setup_log_streaming()
        port = config.dashboard_ws_port
        async with serve(self.handler, "localhost", port):
            print(f"Dashboard WebSocket server running on ws://localhost:{port}")
            await asyncio.Future()  # Run forever
