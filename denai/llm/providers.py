"""Multi-model provider abstraction.

Supports Ollama (default), OpenAI-compatible APIs (LM Studio, LocalAI),
and GPT4All (optional). Each provider normalizes requests/responses to
a common format.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import AsyncGenerator

import httpx

from ..config import OLLAMA_URL
from ..logging_config import get_logger

log = get_logger("providers")


@dataclass
class Provider:
    """A model provider configuration."""

    name: str
    kind: str  # "ollama", "openai", "gpt4all"
    base_url: str
    api_key: str = ""
    models: list[str] = field(default_factory=list)
    default_model: str = ""

    @property
    def is_openai_compatible(self) -> bool:
        return self.kind == "openai"

    @property
    def is_ollama(self) -> bool:
        return self.kind == "ollama"

    @property
    def is_gpt4all(self) -> bool:
        return self.kind == "gpt4all"


# ── Provider Registry ─────────────────────────────────────────────

_providers: dict[str, Provider] = {}


def _init_default_providers() -> None:
    """Register Ollama as the default provider."""
    global _providers
    if "ollama" not in _providers:
        _providers["ollama"] = Provider(
            name="Ollama",
            kind="ollama",
            base_url=OLLAMA_URL.rstrip("/"),
        )


def register_provider(provider: Provider) -> None:
    """Register a new provider."""
    _providers[provider.name.lower()] = provider
    log.info("Provider registrado: %s (%s) em %s", provider.name, provider.kind, provider.base_url)


def get_provider(name: str) -> Provider | None:
    """Get a provider by name."""
    _init_default_providers()
    return _providers.get(name.lower())


def get_all_providers() -> list[Provider]:
    """List all registered providers."""
    _init_default_providers()
    return list(_providers.values())


def get_default_provider() -> Provider:
    """Get the default provider (Ollama)."""
    _init_default_providers()
    return _providers["ollama"]


# ── Model listing ─────────────────────────────────────────────────


async def list_models_for_provider(provider: Provider) -> list[dict]:
    """List available models for a provider."""
    try:
        if provider.is_ollama:
            return await _list_ollama_models(provider)
        if provider.is_openai_compatible:
            return await _list_openai_models(provider)
        if provider.is_gpt4all:
            return _list_gpt4all_models()
    except Exception as e:
        log.error("Erro listando modelos de %s: %s", provider.name, e)
    return []


async def _list_ollama_models(provider: Provider) -> list[dict]:
    """List models from Ollama API."""
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(f"{provider.base_url}/api/tags")
        resp.raise_for_status()
        data = resp.json()
        return [
            {
                "name": m["name"],
                "size": m.get("size", 0),
                "modified": m.get("modified_at", ""),
                "provider": provider.name,
            }
            for m in data.get("models", [])
        ]


async def _list_openai_models(provider: Provider) -> list[dict]:
    """List models from OpenAI-compatible API."""
    headers = {}
    if provider.api_key:
        headers["Authorization"] = f"Bearer {provider.api_key}"
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(f"{provider.base_url}/v1/models", headers=headers)
        resp.raise_for_status()
        data = resp.json()
        return [
            {
                "name": m["id"],
                "size": 0,
                "modified": m.get("created", ""),
                "provider": provider.name,
            }
            for m in data.get("data", [])
        ]


def _list_gpt4all_models() -> list[dict]:
    """List locally available GPT4All models."""
    try:
        from gpt4all import GPT4All  # type: ignore[import-untyped]

        models = GPT4All.list_models()
        return [
            {
                "name": m["filename"],
                "size": m.get("filesize", 0),
                "modified": "",
                "provider": "GPT4All",
            }
            for m in models
        ]
    except ImportError:
        return []
    except Exception:
        return []


# ── Streaming chat adapters ───────────────────────────────────────


async def stream_chat_openai(
    provider: Provider,
    model: str,
    messages: list[dict],
    tools: list[dict] | None = None,
    options: dict | None = None,
) -> AsyncGenerator[dict, None]:
    """Stream chat via OpenAI-compatible API, yielding Ollama-format chunks.

    Converts OpenAI SSE format to Ollama's streaming format so the existing
    tool-calling orchestration in ollama.py can work with any provider.
    """
    headers: dict[str, str] = {"Content-Type": "application/json"}
    if provider.api_key:
        headers["Authorization"] = f"Bearer {provider.api_key}"

    payload: dict = {
        "model": model,
        "messages": _convert_messages_to_openai(messages),
        "stream": True,
    }

    if tools:
        payload["tools"] = _convert_tools_to_openai(tools)

    if options:
        if "temperature" in options:
            payload["temperature"] = options["temperature"]
        if "num_ctx" in options:
            payload["max_tokens"] = options["num_ctx"]

    async with httpx.AsyncClient(timeout=httpx.Timeout(300, connect=10)) as client:
        async with client.stream(
            "POST",
            f"{provider.base_url}/v1/chat/completions",
            json=payload,
            headers=headers,
        ) as resp:
            resp.raise_for_status()
            async for line in resp.aiter_lines():
                if not line.startswith("data: "):
                    continue
                data_str = line[6:]
                if data_str.strip() == "[DONE]":
                    yield {"done": True, "message": {"role": "assistant", "content": ""}}
                    return

                try:
                    chunk = json.loads(data_str)
                except json.JSONDecodeError:
                    continue

                delta = chunk.get("choices", [{}])[0].get("delta", {})

                # Content
                if delta.get("content"):
                    yield {
                        "done": False,
                        "message": {"role": "assistant", "content": delta["content"]},
                    }

                # Tool calls
                if delta.get("tool_calls"):
                    for tc in delta["tool_calls"]:
                        fn = tc.get("function", {})
                        if fn.get("name"):
                            yield {
                                "done": False,
                                "message": {
                                    "role": "assistant",
                                    "content": "",
                                    "tool_calls": [
                                        {
                                            "function": {
                                                "name": fn["name"],
                                                "arguments": fn.get("arguments", {}),
                                            }
                                        }
                                    ],
                                },
                            }


def _convert_messages_to_openai(messages: list[dict]) -> list[dict]:
    """Convert Ollama message format to OpenAI format."""
    result = []
    for msg in messages:
        converted: dict = {"role": msg["role"], "content": msg.get("content", "")}
        if msg.get("tool_calls"):
            converted["tool_calls"] = [
                {
                    "id": f"call_{i}",
                    "type": "function",
                    "function": {
                        "name": tc["function"]["name"],
                        "arguments": (
                            json.dumps(tc["function"]["arguments"])
                            if isinstance(tc["function"]["arguments"], dict)
                            else tc["function"]["arguments"]
                        ),
                    },
                }
                for i, tc in enumerate(msg["tool_calls"])
            ]
        if msg["role"] == "tool":
            converted["tool_call_id"] = msg.get("tool_call_id", "call_0")
        result.append(converted)
    return result


def _convert_tools_to_openai(tools: list[dict]) -> list[dict]:
    """Convert Ollama tools format to OpenAI format."""
    result = []
    for tool in tools:
        fn = tool.get("function", tool)
        result.append(
            {
                "type": "function",
                "function": {
                    "name": fn["name"],
                    "description": fn.get("description", ""),
                    "parameters": fn.get("parameters", {}),
                },
            }
        )
    return result


# ── Load providers from config ────────────────────────────────────


def load_providers_from_config(config: dict) -> None:
    """Load providers from config.yaml 'providers' section.

    Example config:
        providers:
          - name: LM Studio
            kind: openai
            base_url: http://localhost:1234
          - name: GPT4All
            kind: gpt4all
            base_url: ""
    """
    for p in config.get("providers", []):
        try:
            provider = Provider(
                name=p["name"],
                kind=p.get("kind", "openai"),
                base_url=p.get("base_url", ""),
                api_key=p.get("api_key", ""),
                models=p.get("models", []),
                default_model=p.get("default_model", ""),
            )
            register_provider(provider)
        except (KeyError, TypeError) as e:
            log.warning("Provider inválido no config: %s — %s", p, e)
