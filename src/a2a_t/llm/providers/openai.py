"""OpenAI-compatible LLM provider client."""

from __future__ import annotations

import json
import logging
from typing import Any

import httpx
from openai import OpenAI

from a2a_t.llm.errors import LLMConfigError, LLMRuntimeError
from a2a_t.llm.models import LLMClientConfig, LLMResponse
from a2a_t.llm.provider import LLMClient

_JSON_MODE_INSTRUCTION_DEFAULT = (
    "Return a valid JSON object string. "
    "The output must be valid json. "
    "Do not wrap the response in markdown code fences. "
    "Do not include any explanation outside the JSON object."
)


class OpenAIClient(LLMClient):
    """LLM client for providers exposing an OpenAI-compatible chat API."""

    def __init__(self, config: LLMClientConfig, logger: Any | None = None) -> None:
        if not config.api_key.strip():
            raise LLMConfigError(f"{config.provider} client requires a non-empty api_key")
        self._config = config
        self._logger = logger if logger is not None else logging.getLogger(__name__)
        self._client: Any | None = None

    def _get_client(self) -> Any:
        if self._client is not None:
            return self._client
        if not self._config.base_url:
            raise LLMConfigError(f"{self._config.provider} client requires a non-empty base_url")
        client_options: dict[str, Any] = {
            "api_key": self._config.api_key,
            "timeout": self._config.timeout_seconds,
            "base_url": self._config.base_url,
        }
        if not self._config.ssl_verify:
            self._logger.warning(
                "TLS certificate chain and hostname verification are disabled for the %s LLM client"
                " (A2AT_LLM_SSL_VERIFY=false); use only in controlled environments with trusted networks",
                self._config.provider,
            )
            client_options["http_client"] = httpx.Client(verify=False)
        self._client = OpenAI(**client_options)
        return self._client

    def structured(
        self,
        *,
        messages: list[dict[str, str]],
        json_schema: dict[str, Any],
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> LLMResponse:
        """Generate a structured response constrained by a JSON schema."""
        payload = self._build_structured_payload(
            messages=messages,
            json_schema=json_schema,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        try:
            raw_response = self._get_client().chat.completions.create(**payload)
        except LLMConfigError:
            raise
        except Exception as exc:  # pragma: no cover - provider failure path
            raise LLMRuntimeError(f"{self._config.provider} invocation failed: {exc}") from exc
        return self._parse_response(raw_response)

    def _build_structured_payload(
        self,
        *,
        messages: list[dict[str, str]],
        json_schema: dict[str, Any],
        temperature: float | None,
        max_tokens: int | None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "model": self._config.model,
            "messages": self._build_structured_messages(messages, json_schema),
            "response_format": {"type": "json_object"},
        }
        if temperature is not None:
            payload["temperature"] = temperature
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens
        # Java parity: the reasoning effort is only forwarded when configured with a non-blank
        # value, so non-reasoning models never receive the parameter.
        if self._config.reasoning_effort:
            payload["reasoning_effort"] = self._config.reasoning_effort
        return payload

    def _build_structured_messages(
        self,
        messages: list[dict[str, str]],
        json_schema: dict[str, Any],
    ) -> list[dict[str, str]]:
        schema_text = json.dumps(json_schema, ensure_ascii=False)
        return [
            {"role": "system", "content": _JSON_MODE_INSTRUCTION_DEFAULT},
            {"role": "system", "content": f"Return JSON that conforms to this JSON schema: {schema_text}"},
            *messages,
        ]

    def _parse_response(self, response: Any) -> LLMResponse:
        usage = getattr(response, "usage", None)
        return LLMResponse(
            content=self._extract_json_object_string(response),
            model=str(getattr(response, "model", self._config.model)),
            usage={
                "prompt_tokens": int(getattr(usage, "prompt_tokens", 0) or 0),
                "completion_tokens": int(getattr(usage, "completion_tokens", 0) or 0),
            },
            metadata={"response": response},
        )

    def _extract_json_object_string(self, response: Any) -> str:
        raw_content = self._extract_message_text(response)
        # Java parity guard of the reasoning models: a blank content (the reasoning went into the
        # reasoning channel, or the model was rate limited) is a coded response-contract violation,
        # never a silent empty string.
        if raw_content is None or not raw_content.strip():
            raise LLMRuntimeError(f"{self._config.provider} returned empty content (rate limit or model timeout)")
        try:
            parsed = json.loads(raw_content)
        except json.JSONDecodeError as exc:
            raise LLMRuntimeError(f"{self._config.provider} returned invalid json: {exc}") from exc
        if not isinstance(parsed, dict):
            raise LLMRuntimeError(f"{self._config.provider} must return a JSON object string")
        return raw_content

    def _extract_message_text(self, response: Any) -> str:
        choices = getattr(response, "choices", None) or []
        if not choices:
            raise LLMRuntimeError(f"{self._config.provider} response did not include any choices")
        message = getattr(choices[0], "message", None)
        content = getattr(message, "content", None)
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            parts: list[str] = []
            for item in content:
                text = getattr(item, "text", None)
                if text is not None:
                    parts.append(str(text))
                elif isinstance(item, dict) and "text" in item:
                    parts.append(str(item["text"]))
                else:
                    parts.append(str(item))
            return "".join(parts)
        if content is None:
            raise LLMRuntimeError(f"{self._config.provider} response did not include message content")
        return str(content)
