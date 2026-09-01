"""Shared prompt resource loading package (D31: the single resource access layer).

The resource access layer (:mod:`~a2a_t.common.prompt_resources.resource_access`) is the one
access point both the prompt pipeline and the negotiation pipeline read resources through; the
module docstring of :mod:`~a2a_t.common.prompt_resources.resource_access` carries the routing
table. The view models in :mod:`~a2a_t.common.prompt_resources.models` project raw resources into
the shapes the pipelines consume.
"""

from .models import (
    PromptMessages,
    ScenarioDefinition,
    SlotDefinition,
    SlotRange,
    SlotSchema,
    slot_schema_from_json_schema,
)
from .resource_access import (
    LOCAL_FILE_SOURCE_TYPE,
    PACKAGED_SOURCE_TYPE,
    LocalFilePromptResourceAccess,
    PackagedPromptResourceAccess,
    PromptResourceAccess,
    create,
)
from .vocabulary import CANONICAL_KEYS, Vocabulary

__all__ = [
    "CANONICAL_KEYS",
    "LOCAL_FILE_SOURCE_TYPE",
    "PACKAGED_SOURCE_TYPE",
    "LocalFilePromptResourceAccess",
    "PackagedPromptResourceAccess",
    "PromptMessages",
    "PromptResourceAccess",
    "ScenarioDefinition",
    "SlotDefinition",
    "SlotRange",
    "SlotSchema",
    "Vocabulary",
    "create",
    "slot_schema_from_json_schema",
]
