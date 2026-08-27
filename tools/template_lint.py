#!/usr/bin/env python3
"""Deterministic structural validation for bundled A2A-T prompt templates.

This linter intentionally does not call an LLM.  It checks the parts of an
A2A-T template that are safe to enforce in CI: the L0 instruction structure,
Markdown heading syntax, and the contract between template placeholders and
the paired slot JSON Schema.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path

HEADING_PATTERN = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
PLACEHOLDER_PATTERN = re.compile(r"{{\s*([^{}\s]+)\s*}}")

TASK_HEADINGS = {
    "Task Description",
    "Task Type",
    "Task Target",
    "Task Object",
    "Task Context",
    "Constraints",
    "Expected Output",
    "Operation Type",
    "Terminology Explanation",
}
NOTIFICATION_HEADINGS = {
    "Subscription Description",
    "Notification Topic",
    "Subscribe Condition",
    "Notification Data Format",
    "Expected Output",
}
AUTHORIZATION_HEADINGS = {
    "Authorization Policy Operation Type",
    "Authorization Policy Operation Description",
    "Network Operation Authorization Policy List",
    "Expected Output",
}
HEADING_ALIASES = {
    "任务描述": "Task Description",
    "任务类型": "Task Type",
    "任务目标": "Task Target",
    "任务对象": "Task Object",
    "目标对象": "Task Object",
    "任务上下文": "Task Context",
    "约束条件": "Constraints",
    "预期输出": "Expected Output",
    "操作类型": "Operation Type",
    "术语解释": "Terminology Explanation",
    "订阅描述": "Subscription Description",
    "通知主题": "Notification Topic",
    "订阅条件": "Subscribe Condition",
    "通知数据格式": "Notification Data Format",
    "上报通知数据格式": "Notification Data Format",
    "授权策略的操作类型": "Authorization Policy Operation Type",
    "授权策略的操作描述": "Authorization Policy Operation Description",
    "动网操作的授权策略列表": "Network Operation Authorization Policy List",
}


@dataclass(frozen=True)
class LintError:
    path: Path
    line: int
    rule: str
    message: str

    def __str__(self) -> str:
        return f"{self.path}:{self.line}: [{self.rule}] {self.message}"


def canonical_heading(value: str) -> str:
    """Return the canonical heading, accepting bilingual display headings."""
    normalized = value.strip()
    if normalized in TASK_HEADINGS | NOTIFICATION_HEADINGS:
        return normalized
    match = re.fullmatch(r"(.+?)\s*\(([^)]+)\)", normalized)
    candidates = (normalized,) if match is None else (match.group(1).strip(), match.group(2).strip())
    for candidate in candidates:
        if candidate in HEADING_ALIASES:
            return HEADING_ALIASES[candidate]
        if candidate in TASK_HEADINGS | NOTIFICATION_HEADINGS:
            return candidate
    return normalized


def load_schema(schema_path: Path, errors: list[LintError]) -> set[str]:
    try:
        data = json.loads(schema_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        errors.append(LintError(schema_path, 1, "schema-json", f"Cannot load JSON Schema: {error}"))
        return set()
    properties = data.get("properties")
    if not isinstance(properties, dict):
        errors.append(LintError(schema_path, 1, "schema-properties", "Schema must define an object 'properties'."))
        return set()
    property_names = set(properties)
    required = data.get("required", [])
    if not isinstance(required, list) or not all(isinstance(item, str) for item in required):
        errors.append(LintError(schema_path, 1, "schema-required", "Schema 'required' must be an array of strings."))
    else:
        for name in required:
            if name not in property_names:
                errors.append(
                    LintError(schema_path, 1, "schema-required", f"Required slot '{name}' is not in properties.")
                )
    return property_names


def lint_template(template_path: Path, schema_path: Path) -> list[LintError]:
    errors: list[LintError] = []
    schema_slots = load_schema(schema_path, errors)
    try:
        lines = template_path.read_text(encoding="utf-8").splitlines()
    except OSError as error:
        return [*errors, LintError(template_path, 1, "template-read", f"Cannot read template: {error}")]

    headings: list[tuple[int, str, int]] = []
    placeholders: list[tuple[int, str]] = []
    for line_number, line in enumerate(lines, start=1):
        heading_match = HEADING_PATTERN.match(line)
        if heading_match:
            level = len(heading_match.group(1))
            if level == 2:
                headings.append((line_number, canonical_heading(heading_match.group(2)), level))
        placeholders.extend((line_number, slot) for slot in PLACEHOLDER_PATTERN.findall(line))

    heading_names = [name for _, name, _ in headings]
    if "Subscription Description" in heading_names:
        profile = "notification"
    elif "Authorization Policy Operation Type" in heading_names:
        profile = "authorization"
    else:
        profile = "task"
    if profile == "notification":
        allowed_headings = NOTIFICATION_HEADINGS
        required_headings = {"Subscription Description"}
    elif profile == "authorization":
        allowed_headings = AUTHORIZATION_HEADINGS
        required_headings = {"Authorization Policy Operation Type"}
    else:
        allowed_headings = TASK_HEADINGS
        required_headings = {"Task Description"}

    if not headings:
        errors.append(
            LintError(
                template_path,
                1,
                "instruction-missing",
                "Template must contain L0 instructions marked with '##'.",
            )
        )
    for line_number, name, _ in headings:
        if name not in allowed_headings:
            errors.append(
                LintError(
                    template_path,
                    line_number,
                    "instruction-name",
                    f"'{name}' is not valid for the {profile} profile.",
                )
            )
    for name in sorted(required_headings - set(heading_names)):
        errors.append(LintError(template_path, 1, "instruction-required", f"Missing required instruction '{name}'."))
    for name in sorted(set(heading_names)):
        occurrences = [line for line, heading, _ in headings if heading == name]
        if len(occurrences) > 1:
            errors.append(
                LintError(template_path, occurrences[1], "instruction-duplicate", f"Instruction '{name}' is repeated.")
            )

    seen_slots: set[str] = set()
    for line_number, slot in placeholders:
        if slot in seen_slots:
            continue
        seen_slots.add(slot)
        if slot not in schema_slots:
            errors.append(
                LintError(
                    template_path,
                    line_number,
                    "slot-undefined",
                    f"Placeholder '{{{{{slot}}}}}' is missing from {schema_path.name}.",
                )
            )
    for slot in sorted(schema_slots - seen_slots):
        errors.append(LintError(schema_path, 1, "slot-unused", f"Schema slot '{slot}' has no template placeholder."))
    return errors


def lint_resource_root(resource_root: Path) -> list[LintError]:
    errors: list[LintError] = []
    templates_root = resource_root / "templates"
    slots_root = resource_root / "slots"
    if not templates_root.is_dir():
        return [LintError(templates_root, 1, "resource-root", "Missing templates directory.")]
    if not slots_root.is_dir():
        return [LintError(slots_root, 1, "resource-root", "Missing slots directory.")]
    for template_path in sorted(templates_root.rglob("template.md")):
        relative = template_path.relative_to(templates_root)
        schema_path = slots_root / relative.parent / "slot.json"
        if not schema_path.is_file():
            continue
        errors.extend(lint_template(template_path, schema_path))
    for schema_path in sorted(slots_root.rglob("slot.json")):
        relative = schema_path.relative_to(slots_root)
        template_path = templates_root / relative.parent / "template.md"
        if not template_path.is_file():
            errors.append(LintError(schema_path, 1, "template-missing", f"Missing paired template: {template_path}"))
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--resource-root", type=Path, required=True, help="Path to prompt_resources.")
    args = parser.parse_args()
    errors = lint_resource_root(args.resource_root)
    for error in errors:
        print(error, file=sys.stderr)
    if errors:
        print(f"A2A-T template lint failed with {len(errors)} error(s).", file=sys.stderr)
        return 1
    print(f"A2A-T template lint passed: {args.resource_root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
