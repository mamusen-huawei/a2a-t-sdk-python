from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from a2a_t.common.prompt_resources.errors import PromptResourceNotFoundError, PromptResourceParseError
from a2a_t.config.models import PromptRuntimeConfig
from a2a_t.core.errors.catalog import ErrorCatalog
from a2a_t.core.errors.messages import render as render_error_message
from a2a_t.prompt.common.errors import PromptSourceError
from a2a_t.prompt.common.models import PromptReference

from .errors import PromptAnalysisError
from .models import ScenarioResolutionFailure, ScenarioResolutionResult

PREPARATION_STAGE = "preparation"
PROMPT_PARSE_STAGE = "prompt_parse"

#: Default reason rendered into ``scenario.not_matched`` when the recognizer reports none.
DEFAULT_SCENARIO_REASON = "Scenario recognition failed."


def _resource_path_of(error: PromptSourceError | PromptResourceNotFoundError | PromptResourceParseError) -> str:
    """Return the resource path fact of one resource-loading error.

    Loaders carry the path (or the rejected locator) in the exception context; a hand-made
    exception without context falls back to its message so the failure still identifies the
    resource.
    """
    for key in ("path", "locator"):
        value = error.context.get(key)
        if value is not None:
            return str(value)
    return str(error)


class ScenarioResolutionOrchestrator:
    """Resolve a prompt reference from scenario recognition."""

    def __init__(
        self,
        *,
        config: PromptRuntimeConfig,
        scenario_loader: Any,
        prompt_resource_loader: Any,
        scenario_recognizer: Any,
    ) -> None:
        if not isinstance(config, PromptRuntimeConfig):
            raise TypeError("config must be a PromptRuntimeConfig instance.")
        self._config = config
        self._scenario_loader = scenario_loader
        self._prompt_resource_loader = prompt_resource_loader
        self._scenario_recognizer = scenario_recognizer

    def resolve(self, normalized_input: str) -> ScenarioResolutionResult:
        """Return a resolved prompt reference or a standardized failure."""
        try:
            scenarios = self._scenario_loader.load(
                language=self._config.language,
            )
            scenario_prompts = self._prompt_resource_loader.load(
                analysis_action="scenario_recognition",
                language=self._config.language,
            )
        except PromptResourceNotFoundError as error:
            return self._resource_failure(error)
        except PromptResourceParseError as error:
            return self._resource_failure(error)
        except PromptSourceError as error:
            return self._resource_failure(error)

        try:
            recognition_result = self._scenario_recognizer.recognize(
                normalized_input=normalized_input,
                scenarios=scenarios,
                language=self._config.language,
                system_prompt=scenario_prompts.system_prompt,
                user_prompt=scenario_prompts.user_prompt,
            )
        except PromptAnalysisError as error:
            return self._scenario_failure(str(error))
        except Exception as error:
            return self._scenario_failure(str(error))

        if not recognition_result.matched or not recognition_result.scenario_code:
            return self._scenario_failure(recognition_result.error_message or DEFAULT_SCENARIO_REASON)

        for scenario in scenarios:
            if scenario.scenario_code == recognition_result.scenario_code:
                return ScenarioResolutionResult(
                    success=True,
                    reference=PromptReference(
                        scenario_code=scenario.scenario_code,
                        language=self._config.language,
                    ),
                    scenario=scenario,
                )

        return self._scenario_failure(
            f"Scenario recognition returned unsupported scenario_code: {recognition_result.scenario_code}"
        )

    def _resource_failure(
        self,
        error: PromptSourceError | PromptResourceNotFoundError | PromptResourceParseError,
    ) -> ScenarioResolutionResult:
        """Build the ``template.load_failed`` failure for one resource-loading error."""
        resource_path = _resource_path_of(error)
        return self._failure(
            stage=PREPARATION_STAGE,
            entry=ErrorCatalog.TEMPLATE_LOAD_FAILED,
            facts={"resource_path": resource_path},
        )

    def _scenario_failure(self, reason: str) -> ScenarioResolutionResult:
        """Build the ``scenario.not_matched`` failure carrying the recognition reason."""
        return self._failure(
            stage=PROMPT_PARSE_STAGE,
            entry=ErrorCatalog.SCENARIO_NOT_MATCHED,
            facts={"reason": reason},
        )

    def _failure(self, *, stage: str, entry: ErrorCatalog, facts: Mapping[str, object]) -> ScenarioResolutionResult:
        return ScenarioResolutionResult(
            success=False,
            failure=ScenarioResolutionFailure(
                code=entry.value,
                message=render_error_message(entry, facts, self._config.language),
                stage=stage,
            ),
        )
