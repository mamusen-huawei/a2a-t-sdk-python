"""Data models for LLM integration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class LLMResponse:
    """Response from an LLM adapter."""

    content: str
    model: str
    usage: dict[str, int]
    metadata: dict[str, Any]
    session_id: str | None = None


@dataclass(frozen=True)
class LLMClientConfig:
    """Resolved default configuration for the shared LLM client.

    Attributes:
        reasoning_effort: optional reasoning effort for reasoning models, one of
            ``none``/``minimal``/``low``/``medium``/``high``/``xhigh`` (already normalized to lower
            case); ``None`` leaves the provider parameter unset. Java ``LLMClientConfig.reasoningEffort``.
    """

    provider: str
    model: str
    api_key: str
    base_url: str | None
    history_window: int
    max_tokens: int | None
    temperature: float | None
    timeout_seconds: float | None
    session_max_total: int
    session_max_per_provider: int
    reasoning_effort: str | None = None
