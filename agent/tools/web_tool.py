"""Web fetching tool — allows agent to fetch data from APIs and websites."""

from __future__ import annotations

from typing import Any

import httpx


class WebTool:
    """Agent tool for HTTP requests and web data fetching."""

    def __init__(self):
        self.client = httpx.AsyncClient(timeout=30.0, follow_redirects=True)

    async def __call__(self, params: dict[str, Any]) -> dict[str, Any]:
        operation = params.get("operation", "fetch")
        handlers = {
            "fetch": self.fetch,
            "post": self.post,
            "json_api": self.json_api,
        }
        handler = handlers.get(operation)
        if not handler:
            return {"error": f"Unknown operation: {operation}"}
        return await handler(params)

    async def fetch(self, params: dict) -> dict:
        url = params.get("url", "")
        try:
            resp = await self.client.get(url)
            return {
                "status": resp.status_code,
                "content": resp.text[:5000],
                "content_type": resp.headers.get("content-type", ""),
            }
        except Exception as e:
            return {"error": str(e)}

    async def post(self, params: dict) -> dict:
        url = params.get("url", "")
        body = params.get("body", {})
        headers = params.get("headers", {})
        try:
            resp = await self.client.post(url, json=body, headers=headers)
            return {
                "status": resp.status_code,
                "content": resp.text[:5000],
            }
        except Exception as e:
            return {"error": str(e)}

    async def json_api(self, params: dict) -> dict:
        url = params.get("url", "")
        try:
            resp = await self.client.get(url)
            return {
                "status": resp.status_code,
                "data": resp.json() if resp.status_code == 200 else None,
                "error": None if resp.status_code == 200 else resp.text[:500],
            }
        except Exception as e:
            return {"error": str(e)}
