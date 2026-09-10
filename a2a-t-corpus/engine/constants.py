"""Shared constants of the accuracy verification corpus (port of the Java ``CorpusWorkFlowSuite`` constants)."""

from __future__ import annotations

from typing import Final

__all__ = [
    "API_GENERATE_TASK_FROM_DATA",
    "API_GENERATE_TASK_FROM_TEXT",
    "API_VALIDATE_TASK",
    "FLOW_FROM_DATA",
    "FLOW_FROM_TEXT",
    "INPUT_CASE_FROM_DATA",
    "INPUT_CASE_FROM_TEXT",
    "TASK_API_NAMES",
]

#: Case file consumed by the natural-language workflow suites.
INPUT_CASE_FROM_TEXT: Final[str] = "input_case_from_text.json"

#: Case file consumed by the structured-input workflow suites.
INPUT_CASE_FROM_DATA: Final[str] = "input_case_from_data.json"

#: Flow tag of the natural-language suites (transcript and summary file names).
FLOW_FROM_TEXT: Final[str] = "from_text"

#: Flow tag of the structured-input suites.
FLOW_FROM_DATA: Final[str] = "from_data"

#: Task-T client generation API (natural language -> task prompt).
API_GENERATE_TASK_FROM_TEXT: Final[str] = "generateTaskPromptFromText"

#: Task-T client generation API (structured data -> task prompt).
API_GENERATE_TASK_FROM_DATA: Final[str] = "generateTaskPromptFromDataWithSchema"

#: Task-T server validation API (prompt validation + parameter extraction).
API_VALIDATE_TASK: Final[str] = "validateTaskPromptAndDataFilling"

#: Task-T phase-1 API names, used for load-time membership checks without touching the LLM runtime.
TASK_API_NAMES: Final[frozenset[str]] = frozenset(
    {API_GENERATE_TASK_FROM_TEXT, API_GENERATE_TASK_FROM_DATA, API_VALIDATE_TASK}
)
