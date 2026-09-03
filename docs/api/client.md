# Client

The client facade is the client-side entry point of the SDK: it generates task prompts (through scenario recognition, or addressed to one explicit template), generates negotiation messages of the Negotiation-T extension, validates incoming negotiation messages, and queries the template catalog.

Every method of the facade takes the template URI in its raw string spelling (for example `Negotiation-T/information-negotiation/propose/v1`) and parses it fail-fast; use the constants of `a2a_t.core.standard_templates` instead of hand-written URI strings.

::: a2a_t.client.a2at_client.A2ATClient

## Result models

`generate_task_prompt` reports failures in its result object instead of raising: the LLM participates in that pipeline, so a failed generation is an expected outcome rather than an exceptional one.

::: a2a_t.client.prompt_generation.models.PromptGenerationResult

::: a2a_t.client.prompt_generation.models.PromptGenerationFailure
