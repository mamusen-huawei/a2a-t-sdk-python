# Server

The server facade is the server-side entry point of the SDK: it checks processed task prompts for compliance, validates extension content prompts and extracts their parameters per a caller-provided schema, generates and validates negotiation messages of the Negotiation-T extension, and queries the template catalog.

Every method of the facade takes the template URI in its raw string spelling (for example `Task-T/network-layer/ran-energy-saving/v1`) and parses it fail-fast; use the constants of `a2a_t.core.standard_templates` instead of hand-written URI strings.

::: a2a_t.server.a2at_server.A2ATServer

## Result models

`check_task_prompt` reports failures in its result object instead of raising; the other validate methods raise catalog-coded exceptions of the error tree.

::: a2a_t.server.prompt_compliance.models.PromptComplianceResult

::: a2a_t.server.prompt_compliance.models.PromptComplianceFailure
