"""Assembly of one negotiation generation orchestrator (port of Java ``NegotiationGenerationOrchestratorBuilder``).

The Java fluent builder is replaced by one keyword-argument configuration dataclass plus its
:meth:`build` method (port plan 2.3: Python has no overloaded-constructor tradition), so the
collaborators are injected as plain keyword arguments instead of chained setters.

The language is required. The LLM client is optional: without one the from-data generation still
works, while the LLM steps of the from-text generation fail with the ``llm.not_configured`` code
inside the extractor. Every generation collaborator has a default implementation wired from the
language (packaged templates and the routed negotiation vocabulary, D31), and each of them can be
overridden for testing or customization.

The validation-leg collaborators of the Java builder (the compliance checker and the semantic
validator) are collapsed into the single :class:`~a2a_t.negotiation.generation.orchestrator.NegotiationParamExtractor`
seam here: the concrete default extractor is delivered by the P6 validation pipeline, so until then
the validation leg runs only with an explicitly injected extractor and fails with a clear wiring
error when called without one (never with a fake partial result).

Two deliberate divergences from the Java builder: the template loader seam is the common resource
access layer (``resource_access``) rather than a negotiation-private loader (D31 — the Java
``DefaultNegotiationTemplateLoader`` is not ported), and the logger seam is dropped because Python
routes pipeline events through the standard :mod:`logging` hierarchy
(``a2a_t.negotiation.generation.orchestrator``), which callers can configure without injection.
"""

from __future__ import annotations

from dataclasses import dataclass

from a2a_t.common.prompt_resources.resource_access import (
    PackagedPromptResourceAccess,
    PromptResourceAccess,
)
from a2a_t.config.models import DEFAULT_LLM_MAX_ATTEMPTS
from a2a_t.core.errors.input_limit import DEFAULT_MAX_TEXT_CHARS, InputLimitConfig
from a2a_t.llm.provider import LLMClient

from ..content.vocabulary import Vocabulary
from .content_extractor import DefaultNegotiationContentExtractor, NegotiationContentExtractor
from .orchestrator import NegotiationGenerationOrchestrator, NegotiationParamExtractor

__all__ = [
    "NegotiationGenerationOrchestratorBuilder",
    "builder",
]


@dataclass(slots=True)
class NegotiationGenerationOrchestratorBuilder:
    """Configuration of one :class:`~a2a_t.negotiation.generation.orchestrator.NegotiationGenerationOrchestrator`.

    Attributes:
        language: language of the generated and validated messages, such as ``zh-CN`` or ``en-US``;
            required.
        llm_client: LLM client used by the LLM steps of the pipelines; ``None`` keeps the LLM steps
            unavailable while the deterministic steps keep working.
        max_attempts: how often one retryable LLM step is attempted before its failure is
            surfaced, at least 1.
        max_text_chars: maximum length in characters accepted for free-text inputs before they
            reach an LLM step, at least 1; oversized inputs fail fast with the code
            ``input.text_too_long`` instead of overflowing the LLM context.
        resource_access: resource access object resolving the negotiation templates and the
            vocabulary; ``None`` uses the packaged access (the D31 replacement of the Java
            classpath-fixed template loader).
        content_extractor: extractor turning free text into typed negotiation content; ``None``
            wires the default extractor over :attr:`llm_client`.
        param_extractor: parameter extractor of the validation leg (P6 seam); ``None`` keeps that
            leg unwired.
    """

    language: str | None = None
    llm_client: LLMClient | None = None
    max_attempts: int = DEFAULT_LLM_MAX_ATTEMPTS
    max_text_chars: int = DEFAULT_MAX_TEXT_CHARS
    resource_access: PromptResourceAccess | None = None
    content_extractor: NegotiationContentExtractor | None = None
    param_extractor: NegotiationParamExtractor | None = None

    def build(self) -> NegotiationGenerationOrchestrator:
        """Assemble the orchestrator from the configured inputs.

        Returns:
            the assembled negotiation generation orchestrator.

        Raises:
            ValueError: when the language is missing or blank, the attempt limit is below 1, or
                the text-length limit is below 1 (Java ``IllegalStateException`` parity: wiring
                errors outside the coded business tree).
            A2ATError: carrying ``infra.resource_read_failed`` when the language has no bundled
                vocabulary (the routed-loader replacement of the Java
                ``IllegalArgumentException``).
        """
        if self.language is None or not self.language.strip():
            raise ValueError("Negotiation language must be configured.")
        if self.max_attempts < 1:
            raise ValueError(f"Negotiation LLM max attempts must be at least 1 but was {self.max_attempts}.")
        if self.max_text_chars < 1:
            raise ValueError(f"Negotiation max text chars must be at least 1 but was {self.max_text_chars}.")
        effective_access = self._effective_access()
        vocabulary = Vocabulary.for_language(self.language, access=effective_access)
        effective_content_extractor = (
            self.content_extractor
            if self.content_extractor is not None
            else DefaultNegotiationContentExtractor(
                self.llm_client,
                max_attempts=self.max_attempts,
                input_limit=InputLimitConfig(self.max_text_chars),
            )
        )
        return NegotiationGenerationOrchestrator(
            language=self.language,
            max_text_chars=self.max_text_chars,
            resource_access=effective_access,
            content_extractor=effective_content_extractor,
            param_extractor=self.param_extractor,
            vocabulary=vocabulary,
        )

    def _effective_access(self) -> PromptResourceAccess:
        """Return the injected resource access or the packaged default."""
        return PackagedPromptResourceAccess() if self.resource_access is None else self.resource_access


def builder() -> NegotiationGenerationOrchestratorBuilder:
    """Create one new orchestrator builder with every field at its default.

    Returns:
        an empty orchestrator builder; set the language and any collaborator override, then call
        :meth:`NegotiationGenerationOrchestratorBuilder.build`.
    """
    return NegotiationGenerationOrchestratorBuilder()
