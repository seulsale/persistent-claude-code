from __future__ import annotations

import shutil
from pathlib import Path

_FALLBACK_PATHS = [
    "~/.local/bin/claude",
    "/usr/local/bin/claude",
]


def resolve_claude_binary(override: str | None) -> str | None:
    if override:
        return override if Path(override).is_file() else None

    on_path = shutil.which("claude")
    if on_path is not None:
        return on_path

    for candidate in _FALLBACK_PATHS:
        expanded = Path(candidate).expanduser()
        if expanded.is_file():
            return str(expanded)

    return None
