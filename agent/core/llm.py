"""LLM interface for AgentProof — supports OpenRouter (default), Gemini, Anthropic, and OpenAI."""

from __future__ import annotations

import json
from typing import Any

from .config import config
from .models import BudgetTracker


class LLMClient:
    """Unified LLM interface with budget tracking. OpenRouter + GPT-4.1-mini is default."""

    def __init__(self, budget: BudgetTracker):
        self.budget = budget
        self.provider = config.llm_provider
        self.model = config.llm_model
        self._client = None

    def _get_client(self):
        if self._client is None:
            if self.provider == "openrouter":
                import openai
                self._client = openai.OpenAI(
                    api_key=config.openrouter_api_key,
                    base_url="https://openrouter.ai/api/v1",
                )
            elif self.provider == "gemini":
                from google import genai
                self._client = genai.Client(api_key=config.gemini_api_key)
            elif self.provider == "anthropic":
                import anthropic
                self._client = anthropic.Anthropic(api_key=config.anthropic_api_key)
            else:  # openai direct
                import openai
                self._client = openai.OpenAI(api_key=config.openai_api_key)
        return self._client

    def complete_sync(
        self,
        system_prompt: str,
        user_message: str,
        temperature: float = 0.7,
        max_retries: int = 2,
    ) -> str:
        """Synchronous completion with retry — primary method used by agent loop."""
        client = self._get_client()

        if not self.budget.can_spend(0.005):
            return '{"error": "Budget exceeded"}'

        last_error = None
        for attempt in range(max_retries + 1):
            try:
                if self.provider == "openrouter":
                    content = self._openrouter_complete(client, system_prompt, user_message, temperature)
                elif self.provider == "gemini":
                    content = self._gemini_complete(client, system_prompt, user_message, temperature)
                elif self.provider == "anthropic":
                    content = self._anthropic_complete(client, system_prompt, user_message, temperature)
                else:
                    content = self._openai_complete(client, system_prompt, user_message, temperature)

                self.budget.record_llm_call(0.005)
                return content

            except Exception as e:
                last_error = e
                if attempt < max_retries:
                    import time
                    time.sleep(1)
                    continue

        self.budget.record_llm_call(0.001)
        return json.dumps({"error": str(last_error)})

    def _openrouter_complete(self, client, system_prompt: str, user_message: str, temperature: float) -> str:
        """Call OpenRouter API (OpenAI-compatible). Default: openai/gpt-4.1-mini."""
        response = client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            temperature=temperature,
            max_tokens=4096,
        )
        return response.choices[0].message.content or ""

    def _gemini_complete(self, client, system_prompt: str, user_message: str, temperature: float) -> str:
        """Call Google Gemini API."""
        from google.genai import types

        response = client.models.generate_content(
            model=self.model,
            contents=f"{user_message}",
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                temperature=temperature,
                max_output_tokens=4096,
                response_mime_type="text/plain",
            ),
        )
        return response.text or ""

    def _anthropic_complete(self, client, system_prompt: str, user_message: str, temperature: float) -> str:
        """Call Anthropic Claude API."""
        response = client.messages.create(
            model=self.model,
            max_tokens=4096,
            temperature=temperature,
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}],
        )
        return "".join(b.text for b in response.content if b.type == "text")

    def _openai_complete(self, client, system_prompt: str, user_message: str, temperature: float) -> str:
        """Call OpenAI API directly."""
        response = client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            temperature=temperature,
        )
        return response.choices[0].message.content or ""

    async def complete(
        self,
        system_prompt: str,
        user_message: str,
        temperature: float = 0.7,
    ) -> dict[str, Any]:
        """Async completion wrapper."""
        content = self.complete_sync(system_prompt, user_message, temperature)
        return {"content": content, "tool_calls": []}
