from __future__ import annotations

import logging
from collections.abc import Mapping
from typing import Any

from a2a_t.common.prompt_resources import PromptResourceAccess
from a2a_t.common.prompt_resources.models import PromptMessages, SlotSchema, slot_schema_from_json_schema
from a2a_t.config.models import PromptRuntimeConfig
from a2a_t.core.errors.catalog import ErrorCatalog
from a2a_t.core.errors.exceptions import A2ATBusinessError, A2ATError
from a2a_t.core.errors.input_limit import InputLimitConfig
from a2a_t.core.errors.messages import render as render_error_message
from a2a_t.core.prompt_resource_key import PromptResourceKey
from a2a_t.llm.errors import LLMConfigError, is_response_contract_violation
from a2a_t.prompt.analysis import ScenarioResolutionOrchestrator
from a2a_t.prompt.analysis.errors import PromptAnalysisError
from a2a_t.prompt.analysis.scenario_resolution_orchestrator import (
    DEFAULT_SCENARIO_REASON,
    PREPARATION_STAGE,
)
from a2a_t.prompt.common.models import PromptReference
from a2a_t.prompt.task_rendering import TaskPromptRenderer
from a2a_t.prompt.task_rendering.errors import TaskPromptRenderError

from .generation_constants import GENERATION_STAGE, INPUT_STAGE, RENDER_STAGE, SCENARIO_STAGE
from .input_normalizer import InputNormalizer
from .models import PromptGenerationFailure, PromptGenerationResult

_LOGGER = logging.getLogger(__name__)

#: Step label reported in ``llm.response_invalid`` when the slot-extraction step fails.
_STEP_SLOT_EXTRACTION = "slot extraction"

#: Analysis action whose system/user prompts drive slot extraction.
_SLOT_EXTRACTION_ACTION = "slot_extraction"


class PromptGenerationOrchestrator:
    """Coordinate the full client-side prompt generation pipeline.

    Every resource — template text, slot schema and the slot-extraction instruction prompts — is
    loaded through the shared resource access layer (D31): templates and slot schemas follow the
    configured source routing, the instruction prompts are always the packaged SDK contract.
    """

    def __init__(
        self,
        *,
        config: PromptRuntimeConfig,
        resource_access: PromptResourceAccess,
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
        self._resource_access = resource_access
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
    ) -> tuple[str, str, SlotSchema, PromptMessages]:
        """Load generation resources through the shared resource access layer.

        The access layer already raises the artifact-specific catalog codes — ``template.not_found``
        for a missing template, ``slot.schema_not_found`` for a missing slot schema — so the
        business failures pass straight through; every other access failure maps to
        ``template.load_failed`` with the failing resource path as the fact.
        """
        try:
            template_text = self._resource_access.template_text(reference.scenario_code, reference.language)
            slot_json_schema = self._resource_access.slot_schema(reference.scenario_code, reference.language)
            slot_schema = slot_schema_from_json_schema(
                slot_json_schema,
                scenario_code=reference.scenario_code,
            )
        except A2ATBusinessError as error:
            raise _PromptGenerationResourceError(
                entry=error.code,
                facts=error.facts,
                stage=PREPARATION_STAGE,
            ) from error
        except A2ATError as error:
            raise _PromptGenerationResourceError(
                entry=ErrorCatalog.TEMPLATE_LOAD_FAILED,
                facts={"resource_path": reference.scenario_code},
                stage=PREPARATION_STAGE,
            ) from error
        try:
            slot_prompts = PromptMessages(
                system_prompt=self._resource_access.load_prompt(
                    _SLOT_EXTRACTION_ACTION, reference.language, "system.md"
                ),
                user_prompt=self._resource_access.load_prompt(_SLOT_EXTRACTION_ACTION, reference.language, "user.md"),
            )
        except A2ATError as error:
            raise _PromptGenerationResourceError(
                entry=ErrorCatalog.TEMPLATE_LOAD_FAILED,
                facts={
                    "resource_path": PromptResourceKey.prompt(
                        _SLOT_EXTRACTION_ACTION, reference.language, "system.md"
                    ).relative_path()
                },
                stage=PREPARATION_STAGE,
            ) from error
        return reference.language, template_text, slot_schema, slot_prompts

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
