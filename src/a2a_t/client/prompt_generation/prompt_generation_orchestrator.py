from __future__ import annotations

import logging
from collections.abc import Mapping
from typing import Any

from a2a_t.common.prompt_resources import (
    PromptResourceNotFoundError,
    PromptResourceParseError,
)
from a2a_t.config.models import PromptRuntimeConfig
from a2a_t.core.errors.catalog import ErrorCatalog
from a2a_t.core.errors.input_limit import InputLimitConfig
from a2a_t.core.errors.messages import render as render_error_message
from a2a_t.llm.errors import LLMConfigError, is_response_contract_violation
from a2a_t.prompt.analysis import ScenarioResolutionOrchestrator
from a2a_t.prompt.analysis.errors import PromptAnalysisError
from a2a_t.prompt.analysis.scenario_resolution_orchestrator import (
    DEFAULT_SCENARIO_REASON,
    PREPARATION_STAGE,
)
from a2a_t.prompt.common.errors import PromptSourceError
from a2a_t.prompt.common.models import PromptReference
from a2a_t.prompt.task_rendering import TaskPromptRenderer
from a2a_t.prompt.task_rendering.errors import TaskPromptRenderError

from .generation_constants import GENERATION_STAGE, INPUT_STAGE, RENDER_STAGE, SCENARIO_STAGE
from .input_normalizer import InputNormalizer
from .models import PromptGenerationFailure, PromptGenerationResult

_LOGGER = logging.getLogger(__name__)

#: Step label reported in ``llm.response_invalid`` when the slot-extraction step fails.
_STEP_SLOT_EXTRACTION = "slot extraction"


class PromptGenerationOrchestrator:
    """Coordinate the full client-side prompt generation pipeline."""

    def __init__(
        self,
        *,
        config: PromptRuntimeConfig,
        prompt_resource_loader: Any,
        template_loader: Any,
        slot_schema_loader: Any,
        scenario_resolver: ScenarioResolutionOrchestrator,
        slot_extractor: Any,
        input_normalizer: InputNormalizer | None = None,
        renderer: TaskPromptRenderer | None = None,
        input_limit: InputLimitConfig | None = None,
        logger: Any | None = None,
    ) -> None:
        if not isinstance(config, PromptRuntimeConfig):
            raise TypeError("config must be a PromptRuntimeConfig instance.")
        self._config = config
        self._prompt_resource_loader = prompt_resource_loader
        self._template_loader = template_loader
        self._slot_schema_loader = slot_schema_loader
        self._scenario_resolver = scenario_resolver
        self._slot_extractor = slot_extractor
        self._input_normalizer = input_normalizer or InputNormalizer()
        self._renderer = renderer or TaskPromptRenderer()
        self._input_limit = input_limit if input_limit is not None else InputLimitConfig()
        self._logger = logger if logger is not None else _LOGGER

    def generate(self, user_input: str | dict[str, object]) -> PromptGenerationResult:
        """Run prompt generation from input normalization through prompt rendering."""
        self._log_info("prompt_generation_started")
        if isinstance(user_input, str) and self._input_limit.is_too_long(user_input):
            return self._catalog_failure(
                entry=ErrorCatalog.INPUT_TEXT_TOO_LONG,
                facts=self._input_limit.too_long_facts(user_input),
                stage=INPUT_STAGE,
            )
        if self._is_debug_enabled():
            self._log_debug("prompt_generation_raw_user_input raw_user_input=%s", user_input)
        normalized_input = self._input_normalizer.normalize(user_input)
        language = self._config.language
        self._log_info(
            "prompt_generation_input_normalized input_kind=%s requested_language=%s",
            normalized_input.input_kind,
            language,
        )

        scenario_resolution = self._scenario_resolver.resolve(normalized_input.normalized_input)
        self._log_debug_if_available(
            "prompt_generation_scenario_raw_output scenario_raw_output=%s",
            self._scenario_resolver,
        )
        if (
            not scenario_resolution.success
            or scenario_resolution.reference is None
            or scenario_resolution.scenario is None
        ):
            failure = scenario_resolution.failure
            if failure is None:
                return self._catalog_failure(
                    entry=ErrorCatalog.SCENARIO_NOT_MATCHED,
                    facts={"reason": DEFAULT_SCENARIO_REASON},
                    stage=SCENARIO_STAGE,
                )
            # The resolver already rendered the catalog message for its own failure mode.
            return self._failure_result(code=failure.code, message=failure.message, stage=failure.stage)
        reference = scenario_resolution.reference
        scenario = scenario_resolution.scenario
        scenario_code = reference.scenario_code
        resolved_language = reference.language
        self._log_info(
            "prompt_generation_scenario_recognized scenario_code=%s language=%s",
            scenario_code,
            resolved_language,
        )
        try:
            resolved_language, template_text, slot_schema, slot_prompts = self._load_generation_resources(
                reference=reference,
            )
            reference = PromptReference(scenario_code=scenario_code, language=resolved_language)
        except _PromptGenerationResourceError as error:
            # At this point the scenario is known, so preserve it in the failure payload for callers.
            return self._finalize_result(
                PromptGenerationResult(
                    success=False,
                    prompt_text=None,
                    failure=PromptGenerationFailure(
                        code=error.entry.value,
                        message=render_error_message(error.entry, error.facts, resolved_language),
                        stage=error.stage,
                    ),
                )
            )

        try:
            extraction_result = self._slot_extractor.extract(
                normalized_input=normalized_input.normalized_input,
                reference=reference,
                template_text=template_text,
                slot_schema=slot_schema,
                system_prompt=slot_prompts.system_prompt,
                user_prompt=slot_prompts.user_prompt,
            )
        except PromptAnalysisError:
            return self._catalog_failure(
                entry=ErrorCatalog.LLM_RESPONSE_INVALID,
                facts={"step": _STEP_SLOT_EXTRACTION},
                stage=GENERATION_STAGE,
            )
        except Exception as error:
            return self._llm_failure_result(error, step=_STEP_SLOT_EXTRACTION)
        self._log_debug_if_available(
            "prompt_generation_slot_raw_output slot_raw_output=%s",
            self._slot_extractor,
        )
        rendered_prompt_text, render_error_message_text = self._render_prompt_text(
            template_text=template_text,
            slots=extraction_result.slots,
            scenario_code=scenario_code,
            language=resolved_language,
            description=scenario.description,
        )
        self._log_info(
            "prompt_generation_slots_extracted slots=%s slot_errors=%s",
            extraction_result.slots,
            extraction_result.slot_errors,
        )
        if rendered_prompt_text is None:
            return self._catalog_failure(
                entry=ErrorCatalog.TEMPLATE_RENDER_FAILED,
                facts={
                    "template_uri": scenario_code,
                    "reason": render_error_message_text or "Task prompt rendering failed.",
                },
                stage=RENDER_STAGE,
            )

        return self._finalize_result(
            PromptGenerationResult(
                success=True,
                prompt_text=rendered_prompt_text,
                failure=None,
            )
        )

    def _load_generation_resources(
        self,
        *,
        reference: PromptReference,
    ) -> tuple[str, Any, Any, Any]:
        """Load generation resources and specialize missing-resource failures by artifact type."""
        try:
            template_text = self._template_loader.load(
                reference=reference,
            )
            slot_schema = self._slot_schema_loader.load(
                reference=reference,
            )
            slot_prompts = self._prompt_resource_loader.load(
                analysis_action="slot_extraction",
                language=reference.language,
            )
            return reference.language, template_text, slot_schema, slot_prompts
        except _PromptGenerationResourceError:
            raise
        except PromptResourceNotFoundError as error:
            resource_path = str(error.context.get("path", ""))
            # Different missing artifacts produce different public error codes
            # even though loaders share one exception type.
            if resource_path.endswith("template.md"):
                raise _PromptGenerationResourceError(
                    entry=ErrorCatalog.TEMPLATE_NOT_FOUND,
                    facts={"template_uri": reference.scenario_code, "language": reference.language},
                    stage=PREPARATION_STAGE,
                ) from error
            if resource_path.endswith("slot.json"):
                raise _PromptGenerationResourceError(
                    entry=ErrorCatalog.SLOT_SCHEMA_NOT_FOUND,
                    facts={"template_uri": reference.scenario_code, "language": reference.language},
                    stage=PREPARATION_STAGE,
                ) from error
            raise _PromptGenerationResourceError(
                entry=ErrorCatalog.TEMPLATE_LOAD_FAILED,
                facts={"resource_path": resource_path or str(error)},
                stage=PREPARATION_STAGE,
            ) from error
        except PromptResourceParseError as error:
            raise _PromptGenerationResourceError(
                entry=ErrorCatalog.TEMPLATE_LOAD_FAILED,
                facts={"resource_path": str(error.context.get("path", error))},
                stage=PREPARATION_STAGE,
            ) from error
        except PromptSourceError as error:
            raise _PromptGenerationResourceError(
                entry=ErrorCatalog.TEMPLATE_LOAD_FAILED,
                facts={"resource_path": str(error.context.get("locator", reference.scenario_code))},
                stage=PREPARATION_STAGE,
            ) from error

    def _render_prompt_text(
        self,
        *,
        template_text: str,
        slots: dict[str, str | None],
        scenario_code: str,
        language: str,
        description: str,
    ) -> tuple[str | None, str | None]:
        """Render the final prompt text while preserving renderer failures as data."""
        try:
            return (
                self._renderer.render(
                    template_text=template_text,
                    slots=slots,
                    scenario_code=scenario_code,
                    language=language,
                    description=description,
                ),
                None,
            )
        except TaskPromptRenderError as error:
            return None, str(error)

    def _llm_failure_result(self, error: BaseException, *, step: str) -> PromptGenerationResult:
        """Translate one LLM-step failure into the Java client-orchestrator failure codes.

        Configuration failures map to ``llm.not_configured``, response-contract violations to
        ``llm.response_invalid`` (carrying the step label), and everything else to
        ``llm.invocation_failed`` (carrying the underlying message as the reason fact).
        """
        if isinstance(error, LLMConfigError):
            return self._catalog_failure(
                entry=ErrorCatalog.LLM_NOT_CONFIGURED,
                facts={},
                stage=GENERATION_STAGE,
            )
        if is_response_contract_violation(error):
            return self._catalog_failure(
                entry=ErrorCatalog.LLM_RESPONSE_INVALID,
                facts={"step": step},
                stage=GENERATION_STAGE,
            )
        return self._catalog_failure(
            entry=ErrorCatalog.LLM_INVOCATION_FAILED,
            facts={"reason": str(error)},
            stage=GENERATION_STAGE,
        )

    def _catalog_failure(
        self,
        *,
        entry: ErrorCatalog,
        facts: Mapping[str, object],
        stage: str,
    ) -> PromptGenerationResult:
        """Build a generation failure whose message is rendered from the code's template."""
        return self._failure_result(
            code=entry.value,
            message=render_error_message(entry, facts, self._config.language),
            stage=stage,
        )

    def _failure_result(
        self,
        *,
        code: str,
        message: str,
        stage: str,
    ) -> PromptGenerationResult:
        """Build a standardized generation failure result without scenario context."""
        return self._finalize_result(
            PromptGenerationResult(
                success=False,
                prompt_text=None,
                failure=PromptGenerationFailure(code=code, message=message, stage=stage),
            )
        )

    def _finalize_result(self, result: PromptGenerationResult) -> PromptGenerationResult:
        """Emit completion logs and return the final generation result unchanged."""
        failure_stage = result.failure.stage if result.failure is not None else None
        failure_code = result.failure.code if result.failure is not None else None
        self._log_info(
            "prompt_generation_completed success=%s stage=%s code=%s",
            result.success,
            failure_stage,
            failure_code,
        )
        return result

    def _log_info(self, message: str, *args: object) -> None:
        """Write an info log through the configured logger."""
        self._logger.info(message, *args)

    def _log_debug(self, message: str, *args: object) -> None:
        """Write a debug log only when prompt-generation debug mode is enabled."""
        if self._is_debug_enabled():
            self._logger.debug(message, *args)

    def _log_debug_if_available(self, message: str, source: Any) -> None:
        """Log captured raw model output when the dependency exposes it."""
        raw_content = getattr(source, "last_raw_response_content", None)
        if raw_content is not None:
            self._log_debug(message, raw_content)

    def _is_debug_enabled(self) -> bool:
        """Return whether prompt-generation debug logging is enabled."""
        return bool(getattr(self._config, "prompt_generation_debug", False))


class _PromptGenerationResourceError(Exception):
    """Carry catalog failure details before they are converted into API results."""

    def __init__(self, *, entry: ErrorCatalog, facts: Mapping[str, object], stage: str) -> None:
        super().__init__(entry.value)
        self.entry = entry
        self.facts = dict(facts)
        self.stage = stage
