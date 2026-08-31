from __future__ import annotations

from dataclasses import dataclass

from a2a_t.core.errors.catalog import ErrorCatalog


@dataclass(frozen=True)
class PromptComplianceFailure:
    """Structured description of why a compliance check rejected a prompt.

    Port of the Java ``PromptComplianceFailure`` record (D3): a machine-readable catalog code, a
    message rendered from the code's template, and the compliance stage where the failure
    occurred. The ``code`` is the external string carrier (D4), so a catalog member passed in is
    normalized to its plain string form.

    The ``get``/``__getitem__`` mapping access is a compatibility shim for the legacy negotiation
    demo packages, which still read ``failure.get("stage")``/``failure.get("message")``; it is
    removed together with those packages.
    """

    code: str
    message: str
    stage: str

    def __post_init__(self) -> None:
        if isinstance(self.code, ErrorCatalog):
            object.__setattr__(self, "code", self.code.value)

    def to_dict(self) -> dict[str, str]:
        """Serialize the failure into the public response shape."""
        return {"code": self.code, "message": self.message, "stage": self.stage}

    def __getitem__(self, key: str) -> str:
        """Read one field by its mapping key (``code``/``message``/``stage``)."""
        values = self.to_dict()
        if key in values:
            return values[key]
        raise KeyError(key)

    def get(self, key: str, default: str | None = None) -> str | None:
        """Read one field by its mapping key, returning the default when it is unknown."""
        return self.to_dict().get(key, default)


@dataclass(frozen=True)
class PromptComplianceResult:
    """Unified compliance execution result."""

    success: bool
    failure: PromptComplianceFailure | None = None

    def to_dict(self) -> dict[str, object]:
        """Serialize the compliance result into the public response shape."""
        return {
            "success": self.success,
            "failure": self.failure.to_dict() if self.failure is not None else None,
        }


@dataclass(frozen=True)
class SemanticValidationError:
    slot_name: str
    code: str
    message: str


@dataclass(frozen=True)
class SemanticValidationResult:
    passed: bool
    errors: list[SemanticValidationError]
