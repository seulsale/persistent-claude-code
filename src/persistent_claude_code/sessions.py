from __future__ import annotations

import json
import os
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


TAIL_BYTES = 200 * 1024
UNTITLED = "Untitled session"


@dataclass
class SessionMetadata:
    title: str
    branch: str | None


def _iter_tail_lines(path: Path, n_bytes: int = TAIL_BYTES) -> list[str]:
    with path.open("rb") as fh:
        fh.seek(0, os.SEEK_END)
        size = fh.tell()
        start = max(0, size - n_bytes)
        fh.seek(start)
        chunk = fh.read()
    if start > 0:
        # drop the possibly-partial first line
        first_nl = chunk.find(b"\n")
        if first_nl >= 0:
            chunk = chunk[first_nl + 1:]
    text = chunk.decode("utf-8", errors="replace")
    return [line for line in text.splitlines() if line]


def _extract_user_text(entry: dict) -> str | None:
    message = entry.get("message")
    if not isinstance(message, dict):
        return None
    content = message.get("content")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        for part in content:
            if isinstance(part, dict) and part.get("type") == "text":
                text = part.get("text")
                if isinstance(text, str):
                    return text
    return None


def parse_session_metadata(path: Path) -> SessionMetadata:
    title: str | None = None
    first_user_text: str | None = None
    branch: str | None = None

    for line in _iter_tail_lines(path):
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(entry, dict):
            continue

        t = entry.get("type")
        if t == "last-prompt":
            last_prompt = entry.get("lastPrompt")
            if isinstance(last_prompt, str) and last_prompt.strip():
                title = last_prompt
        elif t == "user" and not entry.get("isSidechain", False):
            text = _extract_user_text(entry)
            if text and first_user_text is None:
                first_user_text = text

        git = entry.get("gitBranch")
        if isinstance(git, str) and git:
            branch = git

    return SessionMetadata(
        title=title or first_user_text or UNTITLED,
        branch=branch,
    )


def resolve_project_cwd(subdir: Path) -> tuple[str, bool]:
    """Return (project_path, exists) for a ~/.claude/projects/<subdir>.

    Prefers the cwd field from any jsonl entry; falls back to decoding the
    directory name.
    """
    jsonls = sorted(subdir.glob("*.jsonl"))
    for jsonl in jsonls:
        for line in _iter_tail_lines(jsonl, n_bytes=64 * 1024):
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue
            cwd = entry.get("cwd") if isinstance(entry, dict) else None
            if isinstance(cwd, str) and cwd:
                return cwd, Path(cwd).is_dir()

    decoded = decode_project_dir(subdir.name)
    return decoded, Path(decoded).is_dir()
