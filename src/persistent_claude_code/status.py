from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Literal

State = Literal["working", "waiting", "idle"]
STATE_WORKING: State = "working"
STATE_WAITING: State = "waiting"
STATE_IDLE: State = "idle"

WORKING_WINDOW_S = 2.0
IDLE_AFTER_S = 5 * 60.0


def compute_state(*, last_mtime: float, last_line_type: str | None, now: float) -> State:
    elapsed = now - last_mtime
    if elapsed <= WORKING_WINDOW_S:
        return STATE_WORKING
    if elapsed <= IDLE_AFTER_S and last_line_type == "assistant":
        return STATE_WAITING
    return STATE_IDLE


def read_last_complete_line_type(path: Path, n_bytes: int = 64 * 1024) -> str | None:
    try:
        with path.open("rb") as fh:
            fh.seek(0, os.SEEK_END)
            size = fh.tell()
            if size == 0:
                return None
            start = max(0, size - n_bytes)
            fh.seek(start)
            chunk = fh.read()
    except OSError:
        return None

    if b"\n" not in chunk:
        return None

    # Drop any trailing partial line (no newline after it).
    trailing_newline = chunk.endswith(b"\n")
    lines = chunk.split(b"\n")
    if not trailing_newline:
        lines = lines[:-1]
    # Filter empties, then walk from the end finding the last that parses.
    for raw in reversed([ln for ln in lines if ln]):
        try:
            entry = json.loads(raw.decode("utf-8", errors="replace"))
        except json.JSONDecodeError:
            continue
        if isinstance(entry, dict):
            t = entry.get("type")
            if isinstance(t, str):
                return t
    return None
