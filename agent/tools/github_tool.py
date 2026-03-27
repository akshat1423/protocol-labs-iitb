"""GitHub tool — allows agent to interact with GitHub API."""

from __future__ import annotations

import os
from typing import Any

import httpx


class GitHubTool:
    """Agent tool for GitHub operations: repos, issues, PRs, code."""

    def __init__(self):
        self.token = os.getenv("GITHUB_TOKEN", "")
        self.client = httpx.AsyncClient(
            base_url="https://api.github.com",
            headers={
                "Authorization": f"token {self.token}" if self.token else "",
                "Accept": "application/vnd.github.v3+json",
            },
            timeout=30.0,
        )

    async def __call__(self, params: dict[str, Any]) -> dict[str, Any]:
        """Route to the appropriate GitHub operation."""
        operation = params.get("operation", "")
        handlers = {
            "search_issues": self.search_issues,
            "create_repo": self.create_repo,
            "create_issue": self.create_issue,
            "get_repo": self.get_repo,
            "list_issues": self.list_issues,
            "create_file": self.create_file,
        }
        handler = handlers.get(operation)
        if not handler:
            return {"error": f"Unknown operation: {operation}"}
        return await handler(params)

    async def search_issues(self, params: dict) -> dict:
        query = params.get("query", "")
        resp = await self.client.get(f"/search/issues?q={query}&per_page=5")
        data = resp.json()
        return {
            "total_count": data.get("total_count", 0),
            "items": [
                {
                    "title": i["title"],
                    "url": i["html_url"],
                    "state": i["state"],
                    "labels": [l["name"] for l in i.get("labels", [])],
                }
                for i in data.get("items", [])[:5]
            ],
        }

    async def create_repo(self, params: dict) -> dict:
        name = params.get("name", "")
        resp = await self.client.post("/user/repos", json={
            "name": name,
            "description": params.get("description", ""),
            "private": params.get("private", False),
            "auto_init": True,
        })
        data = resp.json()
        return {
            "full_name": data.get("full_name"),
            "url": data.get("html_url"),
            "clone_url": data.get("clone_url"),
        }

    async def create_issue(self, params: dict) -> dict:
        repo = params.get("repo", "")
        resp = await self.client.post(f"/repos/{repo}/issues", json={
            "title": params.get("title", ""),
            "body": params.get("body", ""),
            "labels": params.get("labels", []),
        })
        data = resp.json()
        return {"number": data.get("number"), "url": data.get("html_url")}

    async def get_repo(self, params: dict) -> dict:
        repo = params.get("repo", "")
        resp = await self.client.get(f"/repos/{repo}")
        data = resp.json()
        return {
            "full_name": data.get("full_name"),
            "description": data.get("description"),
            "stars": data.get("stargazers_count"),
            "language": data.get("language"),
            "open_issues": data.get("open_issues_count"),
        }

    async def list_issues(self, params: dict) -> dict:
        repo = params.get("repo", "")
        resp = await self.client.get(f"/repos/{repo}/issues?per_page=10")
        items = resp.json()
        return {
            "issues": [
                {"title": i["title"], "number": i["number"], "state": i["state"]}
                for i in items[:10]
                if isinstance(i, dict)
            ]
        }

    async def create_file(self, params: dict) -> dict:
        repo = params.get("repo", "")
        path = params.get("path", "")
        import base64
        content = base64.b64encode(params.get("content", "").encode()).decode()
        resp = await self.client.put(f"/repos/{repo}/contents/{path}", json={
            "message": params.get("message", f"Add {path}"),
            "content": content,
        })
        data = resp.json()
        return {"path": path, "sha": data.get("content", {}).get("sha", "")}
