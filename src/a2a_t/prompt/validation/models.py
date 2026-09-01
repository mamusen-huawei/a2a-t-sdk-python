from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(slots=True)
class SlotValidationError:
    """Describe one slot-level validation problem."""

    slot_name: str
    code: str
    message: str

    def to_dict(self) -> dict[str, object]:
        """Serialize the slot validation error into the public response shape."""
        return asdict(self)


@dataclass(slots=True)
class SlotValidationResult:
    """Represent the combined outcome of slot validation."""

    passed: bool
    slot_errors: list[SlotValidationError]
