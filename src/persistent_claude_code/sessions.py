from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Session:
    id: str
    project_path: str
    title: str
    branch: str | None
    last_activity: float
    jsonl_path: Path


@dataclass
class Project:
    path: str
    exists: bool
    sessions: list[Session] = field(default_factory=list)


@dataclass
class Model:
    projects: list[Project] = field(default_factory=list)


def decode_project_dir(name: str) -> str:
    """Decode a Claude project directory name to a filesystem path.

    Claude encodes paths by replacing `/` with `-`; this encoding is lossy
    for paths that contain literal dashes in a segment. Use `resolve_project_cwd`
    (see this module) for authoritative path resolution from the jsonl.
    """
    if name.startswith("-"):
        return "/" + name[1:].replace("-", "/")
    return name
