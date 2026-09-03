# Introduction

**A2A-T SDK Python** is a Python SDK for telecom agent collaboration scenarios. It generates, validates, and negotiates task prompts in A2A-T interactions, and is suitable for integration by client agents, server agents, and upper-layer orchestration systems.

This release corresponds to the Java `a2a-t-sdk` 1.1.0 capability surface.

- Python requirement: `>=3.12`
- Package name: `a2a-t-sdk`
- License: Apache-2.0
- Runtime dependencies: `jsonschema`, `python-dotenv`, `openai`

## Project Overview

The SDK serves two kinds of users:

- **Client** — generates task prompts from user input (scenario recognition, or text / structured input addressed to one explicit template) and produces negotiation messages of the Negotiation-T extension.
- **Server** — validates processed task prompts against the scenario, template, and slot constraints, extracts their parameters per a caller-provided schema, and validates incoming negotiation messages.

## Core Capabilities

- **Task prompt generation** — the client generates A2A-T-conformant prompt messages from natural language (scenario recognition) or from text / structured input addressed to one explicit template.
- **Server-side prompt validation and parameter filling** — the server validates the A2A-T message submitted by the client and extracts its parameters per a caller-provided JSON schema.
- **Negotiation content API** — twelve methods over the Negotiation-T extension: eight message-generation methods (`generate_{propose,accept,reject,abort}_prompt_from_{data,text}`) and four message-validation methods (`validate_{propose,accept,reject,abort}_prompt_and_data_filling`).
- **Prompt resource management** — built-in scenario, slot, template, vocabulary, and system prompt resources with bilingual (zh-CN / en-US) coverage, plus local-file overrides of the business content.
- **LLM adaptation** — connects to external large language models through OpenAI-compatible APIs, with bounded retries for the retryable failure codes.
- **Structured, bilingual error model** — a closed catalog of 42 machine-readable error codes with fact parameters and bilingual message templates.

## Project Structure

The core code of the repository lives in `src/a2a_t`, with the main modules as follows:

| Module | Purpose |
| --- | --- |
| `client` | Client facade (`A2ATClient`): task prompt generation and negotiation entry points. |
| `server` | Server facade (`A2ATServer`): validation and negotiation entry points for A2A-T messages. |
| `core` | Template addressing (`TemplateUri`, `StandardTemplates`), metadata models, the error catalog, the exception tree, and the shared validation pipeline. |
| `negotiation` | Negotiation content model, generation pipeline, and validation pipeline. |
| `prompt` | Task prompt analysis, rendering (collapse / drop section policies), and validation. |
| `common` | The single prompt resource access layer (packaged / local-file routing) and the template catalog. |
| `config` | Model-related configuration and its `.env` loading logic. |
| `llm` | LLM adaptation layer: client protocol, factory, and the OpenAI-compatible provider. |

Built-in prompt resources are packaged inside the SDK module at `src/a2a_t/prompt_resources`, containing `templates`, `slots`, `scenarios`, `prompts`, `negotiation-vocabulary`, and `errors`.

## Getting Started

Install the SDK, copy the example environment file, and create the facades:

```bash
pip install a2a-t-sdk
cp env.example .env   # every key is optional; an empty file works
```

```python
from pathlib import Path

from a2a_t.client.a2at_client import A2ATClient

client = A2ATClient(env_path=Path(".env"))
result = client.generate_task_prompt(
    "Generate an Incident event subscription task: the notification topic is Incident, "
    "the subscription levels are critical, medium, high, and low, and the notification data "
    "format is DataPart"
)

if result.success:
    print(result.prompt_text)
else:
    print(result.failure.code, result.failure.message)   # structured failure
```

The [User Guide](en/user_guide.md) walks through prompt generation, server-side validation, and a full negotiation round trip; the [Developer Guide](en/developer_guide.md) covers the architecture, the complete API surface, the resource access layer, the error model, and the testing infrastructure.

## Development and Testing

The project uses `uv` as its package manager and `uv_build` as its build backend:

```bash
cd a2a-t-sdk-python
uv sync --dev
uv run pytest
uv run ruff check src tests
uv run mkdocs build --strict   # API reference build (fails on warnings)
```

The `tests/` directory contains the SDK test suite (including the offline negotiation corpus with 234 bilingual expanded units) and the corpus meta-tests. External contributors are encouraged to run the tests and static checks relevant to their change before submitting.

## License

This project is licensed under the [Apache-2.0](https://github.com/project-openan/a2a-t-sdk-python/blob/main/LICENSE) license.
