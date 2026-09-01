"""Configuration data models for a2a_t."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping

from a2a_t.config.source import DotEnvConfigSource
from a2a_t.core.errors.input_limit import InputLimitConfig


def _parse_bool(raw_value: str | None, default: bool) -> bool:
    """Parse a boolean-like environment value with a fallback default."""
    if raw_value is None or not raw_value.strip():
        return default
    return raw_value.strip().lower() in {"1", "true", "yes", "on"}


def _parse_float(raw_value: str | None, default: float) -> float:
    """Parse a float-like environment value with a fallback default."""
    if raw_value is None or not raw_value.strip():
        return default
    return float(raw_value)


def _default_prompt_resource_root_dir() -> str:
    """Return the packaged prompt resource root directory through the access layer (D8/D31).

    The import is deferred on purpose: the resource access package imports this module at import
    time, so the default-root resolution can only reach back into the access layer at call time.
    Non-filesystem layouts (zipapp) have no directory to point at; an empty string then makes
    ``local_file`` mode fail fast with a config error asking for an explicit local root, while
    ``packaged`` mode keeps working unchanged.
    """
    from a2a_t.common.prompt_resources.packaged_access import prompt_resources_root

    root = prompt_resources_root()
    return str(root.resolve()) if root is not None else ""


def _resolve_prompt_resource_root_dir(raw_value: str | None, *, base_dir: Path | None = None) -> str:
    """Resolve prompt resource roots relative to the config file when needed."""
    if raw_value is None or not raw_value.strip():
        return _default_prompt_resource_root_dir()

    candidate = Path(raw_value)
    if candidate.is_absolute():
        return str(candidate.resolve())

    resolved_base_dir = base_dir.resolve() if base_dir is not None else Path.cwd().resolve()
    return str((resolved_base_dir / candidate).resolve())


@dataclass(slots=True)
class PromptRuntimeConfig:
    """Prompt runtime configuration owned by the config package."""

    language: str = "en-US"
    source_type: str = "local_file"
    local_root_dir: str = field(default_factory=_default_prompt_resource_root_dir)

    @classmethod
    def from_mapping(cls, values: Mapping[str, str], *, base_dir: Path | None = None) -> "PromptRuntimeConfig":
        """Build prompt runtime config from raw environment values."""
        return cls(
            language=values.get("A2AT_LANGUAGE", "en-US") or "en-US",
            source_type=values.get("A2AT_PROMPT_SOURCE_TYPE", "local_file") or "local_file",
            local_root_dir=_resolve_prompt_resource_root_dir(
                values.get("A2AT_PROMPT_RESOURCE_LOCAL_ROOT_DIR"),
                base_dir=base_dir,
            ),
        )


@dataclass(slots=True)
class PromptComplianceConfig:
    """Top-level configuration for prompt compliance."""

    enabled: bool = False
    providers: dict[str, dict[str, Any]] = field(default_factory=dict)

    @classmethod
    def from_mapping(cls, values: Mapping[str, str]) -> "PromptComplianceConfig":
        """Build prompt compliance config from raw environment values."""
        return cls(
            enabled=_parse_bool(values.get("A2AT_PROMPT_COMPLIANCE_ENABLED"), False),
        )


@dataclass
class A2ATConfig:
    """Global A2A-T configuration entry point."""

    prompt: PromptRuntimeConfig
    prompt_compliance: PromptComplianceConfig
    input_limits: InputLimitConfig = field(default_factory=InputLimitConfig)

    @classmethod
    def load(cls, env_path: Path) -> A2ATConfig:
        """Load the complete runtime configuration from a .env file."""
        values = DotEnvConfigSource.load(env_path)
        return cls(
            prompt=PromptRuntimeConfig.from_mapping(values, base_dir=env_path.parent),
            prompt_compliance=PromptComplianceConfig.from_mapping(values),
            input_limits=InputLimitConfig.from_map(values),
        )
