"""
Asynchronous client wrappers for interacting with a local Ollama server.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

import httpx

from app.core.settings import get_settings


@dataclass(slots=True)
class OllamaGenerationResult:
    """
    Lightweight container for a text generation response from Ollama.
    """

    model: str
    response: str
    done: bool
    total_duration: int | None = None
    prompt_eval_count: int | None = None
    eval_count: int | None = None
    context: list[int] | None = None

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "OllamaGenerationResult":
        return cls(
            model=str(data.get("model", "")),
            response=str(data.get("response", "")),
            done=bool(data.get("done", False)),
            total_duration=data.get("total_duration"),
            prompt_eval_count=data.get("prompt_eval_count"),
            eval_count=data.get("eval_count"),
            context=data.get("context"),
        )


class OllamaClient:
    """
    Minimal async client for the Ollama `/api/generate` endpoint.
    """

    def __init__(
        self,
        *,
        base_url: str | None = None,
        timeout: float = 120.0,
        http_client: httpx.AsyncClient | None = None,
    ):
        settings = get_settings()
        self.base_url = base_url or settings.ollama_host.rstrip("/")
        self._owns_client = http_client is None
        self._client = http_client or httpx.AsyncClient(
            base_url=self.base_url,
            timeout=timeout,
            headers={"Content-Type": "application/json"},
        )

    async def __aenter__(self) -> "OllamaClient":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        """
        Close the underlying HTTP client if this instance owns it.
        """
        if self._owns_client:
            await self._client.aclose()

    async def generate(
        self,
        *,
        model: str,
        prompt: str,
        system_prompt: str | None = None,
        options: Mapping[str, Any] | None = None,
    ) -> OllamaGenerationResult:
        """
        Issue a completion request to Ollama and return the parsed result.

        Parameters
        ----------
        model:
            Name of the Ollama model to query (e.g. "llama3").
        prompt:
            Full prompt text to send to the model.
        system_prompt:
            Optional system instructions to prepend server-side.
        options:
            Advanced Ollama generation options (temperature, top_p, etc.).
        """
        payload: dict[str, Any] = {
            "model": model,
            "prompt": prompt,
            "stream": False,
        }
        if system_prompt:
            payload["system"] = system_prompt
        if options:
            payload["options"] = dict(options)

        response = await self._client.post("/api/generate", json=payload)
        response.raise_for_status()
        data = response.json()
        return OllamaGenerationResult.from_dict(data)

