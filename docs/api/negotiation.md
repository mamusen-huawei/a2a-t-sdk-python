# Negotiation content

The negotiation content layer implements the Negotiation-T extension: eight message-generation methods (from typed data, deterministic and zero-LLM; and from free text, through one LLM content-extraction step) and four message-validation methods with parameter extraction.

Both facades expose the same surface: every facade negotiation method delegates to exactly one method of the shared `NegotiationContentService`, which is the single definition of the negotiation content-layer API.

::: a2a_t.negotiation.generation.content_service.NegotiationContentService

## Content models

Typed content of the negotiation messages and the input bundles of the from-data generation methods. The dataclasses are pure data carriers by design: they perform no construction-time validation, so invalid content (a blank description, a `None` conclusion) stays representable and is translated into a coded business failure by the generation pipeline at the exact call site that requires the value.

::: a2a_t.negotiation.content.models

## Enums

::: a2a_t.negotiation.content.enums

## Negotiation vocabulary

The negotiation rendering vocabulary: the language-neutral canonical key set and the per-language text constants used as section titles and labels of the negotiation templates.

::: a2a_t.negotiation.content.vocabulary
