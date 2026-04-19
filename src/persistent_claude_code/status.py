from __future__ import annotations

import json
import os
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from gi.repository import Gio

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


OnStateChange = Callable[[State | None], None]


class SessionStatusMonitor:
    """Watches one session jsonl and emits state changes (or None when stopped)."""

    def __init__(self, jsonl_path: Path, on_state: OnStateChange) -> None:
        self._path = jsonl_path
        self._on_state = on_state
        self._last_state: State | None = None
        self._monitor: Gio.FileMonitor | None = None
        self._timer_id: int = 0

    def start(self) -> None:
        if self._monitor is not None:
            return
        from gi.repository import Gio, GLib  # noqa: PLC0415
        file = Gio.File.new_for_path(str(self._path))
        self._monitor = file.monitor_file(Gio.FileMonitorFlags.NONE, None)
        self._monitor.connect("changed", self._on_change)
        self._timer_id = GLib.timeout_add_seconds(1, self._on_tick)
        self._recompute()

    def stop(self) -> None:
        from gi.repository import GLib  # noqa: PLC0415
        if self._timer_id:
            GLib.source_remove(self._timer_id)
            self._timer_id = 0
        if self._monitor is not None:
            self._monitor.cancel()
            self._monitor = None
        if self._last_state is not None:
            self._last_state = None
            self._on_state(None)

    def _on_change(self, *_a: object) -> None:
        self._recompute()

    def _on_tick(self) -> bool:
        self._recompute()
        return True

    def _recompute(self) -> None:
        import time as _time
        try:
            mtime = self._path.stat().st_mtime
        except OSError:
            new_state: State | None = STATE_IDLE
        else:
            last_type = read_last_complete_line_type(self._path)
            new_state = compute_state(last_mtime=mtime, last_line_type=last_type, now=_time.time())
        if new_state != self._last_state:
            self._last_state = new_state
            self._on_state(new_state)
