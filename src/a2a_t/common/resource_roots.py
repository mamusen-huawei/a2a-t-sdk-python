from __future__ import annotations

import os
from importlib.resources import files
from pathlib import Path


def resolve_prompt_resource_root() -> Path:
    """Resolve the packaged prompt resource tree via ``importlib.resources``.

    Works unchanged for source checkouts, installed wheels, and zipapp layouts
    (D8). The returned path is a real filesystem path, which the interim
    local-file loaders require; the P3 resource-access layer replaces this shim.
    """
    return Path(os.fspath(files("a2a_t").joinpath("prompt_resources")))
