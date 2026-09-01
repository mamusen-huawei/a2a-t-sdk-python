# Common

The common package carries the single resource access layer of the A2A-T prompt resource tree (port decision D31) and the template catalog built on top of it. Both the prompt pipeline and the negotiation pipeline read resources through this layer; no other module assembles resource paths or owns resource caches.

## Resource access

The routing facade over the prompt resource tree, selected by `A2AT_PROMPT_SOURCE_TYPE` (`packaged` — the default since 1.1.0 — or `local_file`). The `templates/**`, `slots/**`, `scenarios/**` and `negotiation-vocabulary/**` categories follow the configured source; the `prompts/**` and `errors/**` categories are always packaged, because they are SDK contracts.

::: a2a_t.common.prompt_resources.resource_access

## Template catalog

The directory-driven catalog over the template tree of every extension and the never-throwing query service the client and server facades expose as `get_prompts` / `get_prompt`.

::: a2a_t.common.prompt_resources.catalog

## Resource models

The value types the access layer loads: one prompt template, one scenario definition, one prompt message pair, and the slot schema view of a `slot.json` document.

::: a2a_t.common.prompt_resources.models

## Negotiation vocabulary loader

The strict loader of the negotiation vocabulary: the language-neutral canonical key set every bundled vocabulary file must define exactly, and the per-language text constants bound to it.

::: a2a_t.common.prompt_resources.vocabulary
