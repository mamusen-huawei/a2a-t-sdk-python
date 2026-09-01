# Core

The core package carries the addressing model, the metadata models, and the error model shared by every extension of the SDK.

## Template addressing

A template URI is the structured, always-valid identifier of a content template. It mirrors the resource directory layout one-to-one; the typed form is the identity representation used for comparisons, while the public facades take the raw string form.

::: a2a_t.core.template_uri

The constants of the built-in content templates, published in both spellings (typed and raw URI string). Use these constants instead of hand-written URI strings.

::: a2a_t.core.standard_templates

## Metadata models

The metadata a generated message travels in: the extension URI, the template it was rendered from, and, for negotiation messages, the session context.

::: a2a_t.core.metadata

## Error catalog

The closed catalog of the 42 machine-readable error codes exposed by the SDK, each with its category and its fact parameters. Message templates live in `prompt_resources/errors/{language}/errors.json` and are rendered by the message renderer.

::: a2a_t.core.errors.catalog

## Exceptions

The exception tree of the error model: `A2ATError` is the single root of every SDK processing failure, and the business failures carry the catalog code, the rendered message, and the structured fact values. Programming errors (`None` or malformed arguments) deliberately stay outside the tree as `TypeError` / `ValueError`.

::: a2a_t.core.errors.exceptions

## Error message rendering

The never-throw renderer of the bilingual error message templates.

::: a2a_t.core.errors.messages

## Input limits

The input limit configuration guarding every facade entry point that accepts a free-text string: oversized inputs fail fast before any LLM call instead of overflowing the LLM context.

::: a2a_t.core.errors.input_limit

## Validation pipeline

The shared content validation pipeline (input gate, rule-level gate, retryable semantic gate, deterministic parameter merge) and its result types. `FilledParamData` is the return type of every validate method of the facades.

::: a2a_t.core.validation_pipeline
