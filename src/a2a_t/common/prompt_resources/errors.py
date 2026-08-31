from __future__ import annotations

from a2a_t.core.errors.catalog import ErrorCatalog
from a2a_t.core.errors.exceptions import A2ATError


class PromptResourceError(A2ATError):
    """Base class for shared prompt resource loading errors.

    Part of the :class:`~a2a_t.core.errors.exceptions.A2ATError` tree. The class-level default
    code is ``infra.resource_read_failed``; callers translate it to the artifact-specific catalog
    code (``template.not_found``, ``slot.schema_not_found``, ``template.load_failed``) at their
    boundary, mirroring the Java orchestrator catch points.
    """

    def __init__(
        self,
        message: str,
        *,
        code: ErrorCatalog = ErrorCatalog.INFRA_RESOURCE_READ_FAILED,
        **context: object,
    ) -> None:
        super().__init__(message, code=code)
        self.context = context


class PromptResourceNotFoundError(PromptResourceError):
    """Raised when a required prompt resource file does not exist."""


class PromptResourceParseError(PromptResourceError):
    """Raised when a prompt resource file cannot be parsed."""
