# Changelog

All notable changes to the a2a-t-sdk Python SDK are documented in this file.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/); the project versioning
follows [Semantic Versioning](https://semver.org/).

## [1.1.0] - 2026-09-01

This release aligns the Python SDK with the capability surface of Java a2a-t-sdk 1.1.0
(对应 Java 1.1.0 能力面): the full negotiation content pipeline, the closed error catalog with
bilingual messages, the template query service, the corpus test system, and the packaged prompt
resource tree. The release carries **breaking changes** — read the migration notes below before
upgrading.

### Breaking Changes

#### 1. `A2AT_PROMPT_SOURCE_TYPE` now defaults to `packaged`

Out of the box the SDK now reads prompt resources from the installed package (the counterpart of
the Java `classpath` default) instead of resolving a local directory. If you relied on the old
default, set the variable explicitly in your `.env`:

```dotenv
# Restore the pre-1.1.0 behavior:
A2AT_PROMPT_SOURCE_TYPE=local_file
# Optional when your resources live outside the SDK package:
A2AT_PROMPT_RESOURCE_LOCAL_ROOT_DIR=/path/to/your/prompt_resources
```

Notes:

- With `A2AT_PROMPT_SOURCE_TYPE` unset (or blank), resources now resolve through
  `importlib.resources` from the installed `a2a_t` package — no directory has to exist next to
  your application.
- In `local_file` mode the whole local root is captured once as a frozen snapshot when the SDK
  is constructed; file edits only take effect after a restart (unchanged).
- The LLM instruction prompts (`prompts/`) and error message catalogs (`errors/`) are always
  loaded from the installed package; a local copy under a custom root is ignored with a WARN
  (unchanged).

#### 2. Structured `Failure` dataclass replaces the bare failure dict (D3)

`PromptComplianceResult.failure` is now the frozen dataclass
`a2a_t.server.prompt_compliance.models.PromptComplianceFailure` instead of a plain
`dict[str, str]`.

Before (1.0.0):

```python
result = server.check(processed_prompt_text="...")
if not result.success:
    code = result.failure["code"]        # "slot_validation_error"
    message = result.failure["message"]
    stage = result.failure["stage"]
```

After (1.1.0):

```python
result = server.check(processed_prompt_text="...")
if not result.success:
    code = result.failure.code           # "slot.constraint_violated"
    message = result.failure.message
    stage = result.failure.stage
    # or the public response shape:
    payload = result.to_dict()
```

`failure.get("code")` / `failure["code"]` still work during 1.1.0 as a compatibility shim and are
removed in the next release. Use the attributes or `to_dict()`.

#### 3. Error codes migrated from snake_case strings to catalog dot-codes

All error codes surfaced by the SDK are now members of the closed
`a2a_t.core.errors.catalog.ErrorCatalog` (42 layered `domain.semantic` codes, e.g.
`content.param_missing`), carried by the re-parented `A2ATError`/`A2ATBusinessError` exception
tree. The legacy snake_case string codes are gone. The migration table:

| 1.0.0 code (snake_case)                      | 1.1.0 catalog code                                       |
| -------------------------------------------- | -------------------------------------------------------- |
| `scenario_parse_failed`                      | `scenario.not_matched`                                    |
| `template_not_found`                         | `template.not_found`                                      |
| `slot_schema_not_found`                      | `slot.schema_not_found`                                   |
| `prompt_not_found`                           | `template.load_failed`                                    |
| `prompt_resource_parse_error`                | `template.load_failed` (client) / `infra.resource_read_failed` (server) |
| `prompt_resource_access_error`               | `template.load_failed` (client) / `infra.resource_read_failed` (server) |
| `prompt_resource_load_error` (server)        | `infra.resource_read_failed`                              |
| `template_load_error` (server)               | `template.not_found` / `infra.resource_read_failed`       |
| `slot_schema_load_error` (server)            | `slot.schema_not_found` / `infra.resource_read_failed`    |
| `processed_prompt_parse_error` (server)      | `scenario.not_matched`                                    |
| `invalid_llm_output`                         | `llm.response_invalid`                                    |
| `llm_execution_failed`                       | `llm.invocation_failed` / `llm.not_configured`            |
| `slot_extraction_error` (server)             | `llm.response_invalid` / `llm.invocation_failed`          |
| `slot_validation_error` (server)             | `slot.not_provided` / `slot.constraint_violated` / `slot.rule_violation` |
| `render_failed`                              | `template.render_failed`                                  |
| LLM-returned `missing_input`                 | `slot.not_provided`                                       |
| LLM-returned `invalid_value`                 | `slot.constraint_violated`                                |

Catch points that previously raised flat exception families (`PromptResourceAccessError`,
`PromptResourceParseError`, `PromptAnalysisError`, ...) now raise exceptions re-parented onto the
`A2ATError` tree; the class names are kept, and every exception now carries `code` (an
`ErrorCatalog` member), `code_str` and structured `facts`. Unknown/cross-domain codes returned by
an LLM step never surface raw — they resolve to the per-domain `*.rule_violation` fallback.

#### 4. Old negotiation demo API deprecated (removal in the next release)

The state-machine negotiation demo is retired in favor of the negotiation content pipeline. The
packages `a2a_t.negotiation.{types,store,runtime,handling,rendering,common}` and the facade
methods `A2ATClient` / `A2ATServer` `{start,receive,continue}_negotiation` emit
`DeprecationWarning` on every use/import and will be **removed in the next release**. Migrate to
the negotiation content API: `generate_negotiation_{propose,accept,reject,abort}_prompt_from_data`
/ `..._from_text` and `validate_{propose,accept,reject,abort}_prompt_and_data_filling`, backed by
`a2a_t.negotiation.generation.NegotiationContentService`.

#### 5. Prompt resource tree moved into the package

The resource tree moved from `package_data/prompt_resources/` (resolved in installed layouts
through `sysconfig.get_path("data")/prompt_resources`) to `src/a2a_t/prompt_resources/`, read
through `importlib.resources.files("a2a_t")`. The old `sysconfig`/`package_data` path is no longer
used, and the `[tool.uv.build-backend] data` mapping in `pyproject.toml` is gone — resources are
part of the wheel by construction, so source checkouts, wheel installs, and zipapps all resolve
the same tree.

### Added

- **Negotiation content pipeline and the 12 negotiation APIs** on both `A2ATClient` and
  `A2ATServer`: `generate_negotiation_{propose,accept,reject,abort}_prompt_from_data`,
  `..._from_text`, and `validate_{propose,accept,reject,abort}_prompt_and_data_filling`,
  with the metadata content model (`MetadataContent`/`NegotiationContext`), the 37-key
  negotiation vocabulary, and the 7 bundled `Negotiation-T` templates.
- **Closed error catalog with bilingual messages**: 42 layered codes
  (`a2a_t.core.errors.catalog.ErrorCatalog`) with per-code fact parameters, message templates in
  `errors/{en-US,zh-CN}/errors.json`, and rendering through `a2a_t.core.errors.messages`.
- **Template query service**: `TemplateQueryService` with `PromptTemplate` descriptions and the
  directory-driven template catalog over the routed `templates/` tree.
- **Sectioned renderer** (`a2a_t.prompt.task_rendering`): the Java 1.1.0 sectioned rendering
  strategy alongside the legacy inline-strategy renderer.
- **Corpus test system**: 234 bilingual corpus units ported byte-identical from the Java repo
  (negotiation-cases, golden, scenarios, from_text/from_data/validate suites), meta contract and
  sensitivity tests, a Hypothesis property layer, and the opt-in live-LLM family
  (`A2AT_TEST_LLM_*`, skipped when unconfigured). 24/24 golden parity fixtures render
  byte-identical to the Java SDK output.
- **Input length gates**: free-text inputs are rejected up front with `input.text_too_long`
  (`A2AT_INPUT_TEXT_MAX_CHARS`, default 16384) before any LLM step.
- **LLM runtime hardening**: `A2AT_LLM_MAX_ATTEMPTS` retry budget (range 1–10, default 3) for
  retryable LLM steps, `A2AT_LLM_REASONING_EFFORT` validation, and an empty-response guard.
- **Client prompt-side generation APIs**: `generate_{task,auth,notification}_prompt_from_text` /
  `..._from_data_with_schema`, and server-side
  `validate_{task,notification,auth}_prompt_and_data_filling`.
- **Offline negotiation sample** (`a2a-t-sample/negotiation`): a fully offline closed-loop demo
  with scripted mock LLM responses.
- **Repository-root `env.example`** carrying the full documented `A2AT_*` key inventory
  (prompt runtime, compliance, input limits, LLM runtime, legacy negotiation store, and the
  dev-only live-test `A2AT_TEST_LLM_*` keys).

### Changed

- Version 1.0.0 → 1.1.0, mirroring the Java SDK version whose capability surface this release
  ports.
- `A2AT_PROMPT_SOURCE_TYPE` default `local_file` → `packaged` (see breaking change 1); the
  `packaged` value replaces the Java `classpath` spelling in the Python SDK.
- The single resource access layer (`a2a_t.common.prompt_resources`) now routes every resource
  family — negotiation templates and vocabulary included — while `prompts/` and `errors/` stay
  package-fixed.
- `PromptGenerationResult`/`PromptComplianceResult` failures carry catalog codes and rendered
  messages (see breaking change 2).

### Deprecated

- The state-machine negotiation demo: `a2a_t.negotiation.{types,store,runtime,handling,rendering,common}`
  and the `{start,receive,continue}_negotiation` facade methods (see breaking change 4).

## [1.0.0] - 2026-06-23

Initial public baseline: task/notification prompt generation, prompt compliance validation,
scenario recognition, slot extraction and validation, LLM client integration, and the
state-machine negotiation demo.
