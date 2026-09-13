# ruff: noqa: E402

from __future__ import annotations

import sys
import unittest
from json import dumps
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = PROJECT_ROOT / "src"

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from a2a_t.llm.errors import LLMConfigError, LLMRuntimeError
from a2a_t.llm.factory import LLMClientFactory
from a2a_t.llm.models import LLMClientConfig
from a2a_t.llm.provider import LLMClient


def build_config(provider: str = "openai", base_url: str | None = None) -> LLMClientConfig:
    return LLMClientConfig(
        provider=provider,
        model="gpt-4o-mini",
        api_key="sk-test",
        base_url=base_url,
        history_window=10,
        max_tokens=None,
        temperature=None,
        timeout_seconds=None,
        session_max_total=300,
        session_max_per_provider=100,
    )


class OpenAIClientTest(unittest.TestCase):
    def setUp(self) -> None:
        self.original_clients = dict(LLMClientFactory._clients)
        self.original_client_defaults = dict(LLMClientFactory._client_defaults)

    def tearDown(self) -> None:
        LLMClientFactory._clients = self.original_clients
        LLMClientFactory._client_defaults = self.original_client_defaults

    @patch("a2a_t.llm.providers.openai.OpenAI")
    def test_factory_creates_default_openai_client(self, openai_cls: Mock) -> None:
        openai_cls.return_value = Mock()

        from a2a_t.llm.providers.openai import OpenAIClient

        client = LLMClientFactory.create(
            "openai", build_config(provider="openai", base_url="https://api.openai.com/v1")
        )

        self.assertIsInstance(client, OpenAIClient)
        self.assertIsInstance(client, LLMClient)
        openai_cls.assert_not_called()

    @patch("a2a_t.llm.providers.openai.OpenAI")
    def test_factory_allows_openai_client_without_base_url_until_invocation(self, openai_cls: Mock) -> None:
        client = LLMClientFactory.create("openai", build_config(provider="openai"))

        with self.assertRaisesRegex(LLMConfigError, "base_url"):
            client.structured(messages=[{"role": "user", "content": "extract"}], json_schema={"type": "object"})

        openai_cls.assert_not_called()

    @patch("a2a_t.llm.providers.openai.OpenAI")
    def test_structured_forces_json_mode_and_includes_schema_instruction(self, openai_cls: Mock) -> None:
        sdk_client = Mock()
        sdk_client.chat.completions.create.return_value = SimpleNamespace(
            model="gpt-4o-mini",
            choices=[SimpleNamespace(message=SimpleNamespace(content='{"device_type":"router"}'))],
            usage=SimpleNamespace(prompt_tokens=7, completion_tokens=2),
        )
        openai_cls.return_value = sdk_client

        from a2a_t.llm.providers.openai import OpenAIClient

        client = OpenAIClient(build_config(base_url="https://custom.example/v1"))
        json_schema = {
            "type": "object",
            "properties": {"device_type": {"type": "string"}},
            "required": ["device_type"],
        }

        response = client.structured(
            messages=[{"role": "user", "content": "extract router"}],
            json_schema=json_schema,
            temperature=0.2,
            max_tokens=9,
        )

        self.assertEqual(response.content, '{"device_type":"router"}')
        self.assertEqual(response.model, "gpt-4o-mini")
        self.assertEqual(response.usage["prompt_tokens"], 7)
        self.assertEqual(response.usage["completion_tokens"], 2)
        openai_cls.assert_called_once_with(
            api_key="sk-test",
            base_url="https://custom.example/v1",
            timeout=None,
        )
        payload = sdk_client.chat.completions.create.call_args.kwargs
        self.assertEqual(payload["model"], "gpt-4o-mini")
        self.assertEqual(payload["temperature"], 0.2)
        self.assertEqual(payload["max_tokens"], 9)
        self.assertEqual(payload["response_format"], {"type": "json_object"})
        self.assertEqual(payload["messages"][0]["role"], "system")
        self.assertIn("JSON", payload["messages"][0]["content"])
        self.assertIn(dumps(json_schema, ensure_ascii=False), payload["messages"][1]["content"])
        self.assertEqual(payload["messages"][2], {"role": "user", "content": "extract router"})

    @patch("a2a_t.llm.providers.openai.httpx")
    @patch("a2a_t.llm.providers.openai.OpenAI")
    def test_ssl_verification_disabled_uses_trust_all_http_client(self, openai_cls: Mock, httpx_module: Mock) -> None:
        sdk_client = Mock()
        sdk_client.chat.completions.create.return_value = SimpleNamespace(
            model="gpt-4o-mini",
            choices=[SimpleNamespace(message=SimpleNamespace(content="{}"))],
            usage=SimpleNamespace(prompt_tokens=1, completion_tokens=1),
        )
        openai_cls.return_value = sdk_client

        from dataclasses import replace

        from a2a_t.llm.providers.openai import OpenAIClient

        config = replace(build_config(base_url="https://self-signed.example/v1"), ssl_verify=False)
        client = OpenAIClient(config)

        client.structured(messages=[{"role": "user", "content": "extract"}], json_schema={"type": "object"})

        httpx_module.Client.assert_called_once_with(verify=False)
        self.assertIs(openai_cls.call_args.kwargs["http_client"], httpx_module.Client.return_value)

    @patch("a2a_t.llm.providers.openai.httpx")
    @patch("a2a_t.llm.providers.openai.OpenAI")
    def test_ssl_verification_enabled_by_default_keeps_default_http_client(
        self, openai_cls: Mock, httpx_module: Mock
    ) -> None:
        sdk_client = Mock()
        sdk_client.chat.completions.create.return_value = SimpleNamespace(
            model="gpt-4o-mini",
            choices=[SimpleNamespace(message=SimpleNamespace(content="{}"))],
            usage=SimpleNamespace(prompt_tokens=1, completion_tokens=1),
        )
        openai_cls.return_value = sdk_client

        from a2a_t.llm.providers.openai import OpenAIClient

        client = OpenAIClient(build_config(base_url="https://api.example.test/v1"))

        client.structured(messages=[{"role": "user", "content": "extract"}], json_schema={"type": "object"})

        httpx_module.Client.assert_not_called()
        self.assertNotIn("http_client", openai_cls.call_args.kwargs)

    @patch("a2a_t.llm.providers.openai.OpenAI")
    def test_structured_rejects_non_json_object_response(self, openai_cls: Mock) -> None:
        sdk_client = Mock()
        sdk_client.chat.completions.create.return_value = SimpleNamespace(
            model="gpt-4o-mini",
            choices=[SimpleNamespace(message=SimpleNamespace(content='["not-object"]'))],
            usage=SimpleNamespace(prompt_tokens=1, completion_tokens=1),
        )
        openai_cls.return_value = sdk_client

        from a2a_t.llm.providers.openai import OpenAIClient

        client = OpenAIClient(build_config(base_url="https://api.example.test/v1"))

        with self.assertRaises(LLMRuntimeError):
            client.structured(messages=[{"role": "user", "content": "extract"}], json_schema={"type": "object"})
