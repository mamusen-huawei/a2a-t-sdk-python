from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass


@dataclass(slots=True)
class ScenarioDefinition:
    """Describe one scenario candidate available to scenario recognition."""

    scenario_code: str
    scenario_name: str
    description: str
    example: str


@dataclass(slots=True)
class PromptMessages:
    """Bundle the system and user prompts used for one analysis action."""

    system_prompt: str
    user_prompt: str


@dataclass(slots=True)
class SlotRange:
    """Describe the optional numeric range constraint of a slot."""

    min: float | int | None
    max: float | int | None


@dataclass(slots=True)
class SlotDefinition:
    """Describe one slot expected by a scenario template."""

    name: str
    required: bool
    description: str
    example: str
    value_constraint: str
    type: str | None
    allowed_values: list[object] | None
    range: SlotRange | None
    pattern: str | None


@dataclass(slots=True)
class SlotSchema:
    """Describe all slots defined for one scenario resource."""

    scenario_code: str
    slots: list[SlotDefinition]


def slot_schema_from_json_schema(data: Mapping[str, object], *, scenario_code: str) -> SlotSchema:
    """Project one standard JSON Schema document into the flat slot schema view.

    Port of the Java ``PromptSlotJsonSchema.toPromptSlotSchema`` model projection: the prompt
    pipeline loads the raw ``slot.json`` document through the resource access layer
    (:meth:`~a2a_t.common.prompt_resources.resource_access.PromptResourceAccess.slot_schema`) and
    uses this projection to obtain the slot view consumed by slot extraction. Unknown keys are
    ignored, mirroring the Java ``@JsonIgnoreProperties`` leniency.

    Args:
        data: raw JSON Schema object of a ``slot.json`` resource.
        scenario_code: scenario code the schema was resolved for.

    Returns:
        the flattened slot schema of the document.
    """
    properties = data.get("properties")
    if not isinstance(properties, Mapping):
        properties = {}
    raw_required = data.get("required")
    required_names: set[str] = {str(item) for item in raw_required} if isinstance(raw_required, list) else set()
    slots = [
        _slot_definition_from_property(
            name=str(name),
            property_schema=property_schema,
            required=bool(name in required_names),
        )
        for name, property_schema in properties.items()
    ]
    return SlotSchema(scenario_code=scenario_code, slots=slots)


def _slot_definition_from_property(
    *,
    name: str,
    property_schema: object,
    required: bool,
) -> SlotDefinition:
    """Normalize one JSON Schema property into the shared slot definition model."""
    if not isinstance(property_schema, Mapping):
        property_schema = {}

    examples = property_schema.get("examples")
    example = ""
    if isinstance(examples, list) and examples:
        example = str(examples[0])

    allowed_values = property_schema.get("x-a2at-allowed-values")
    if allowed_values is None:
        allowed_values = property_schema.get("enum")
    if allowed_values is not None and not isinstance(allowed_values, list):
        allowed_values = [allowed_values]

    slot_range = None
    minimum = property_schema.get("minimum")
    maximum = property_schema.get("maximum")
    if minimum is not None or maximum is not None:
        slot_range = SlotRange(min=minimum, max=maximum)

    slot_type = property_schema.get("x-a2at-slot-type")
    if slot_type is None:
        slot_type = property_schema.get("type")

    return SlotDefinition(
        name=name,
        required=required,
        description=str(property_schema.get("description") or ""),
        example=example,
        value_constraint=str(property_schema.get("x-a2at-value-constraint") or ""),
        type=str(slot_type) if slot_type is not None else None,
        allowed_values=allowed_values,
        range=slot_range,
        pattern=str(property_schema["pattern"]) if property_schema.get("pattern") is not None else None,
    )
