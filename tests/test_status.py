import json
from pathlib import Path

from persistent_claude_code.status import (
    STATE_IDLE,
    STATE_WAITING,
    STATE_WORKING,
    compute_state,
    read_last_complete_line_type,
)


def _write(path: Path, lines: list[dict]) -> None:
    path.write_text("\n".join(json.dumps(line) for line in lines) + "\n")


def test_working_when_modified_within_two_seconds() -> None:
    assert compute_state(last_mtime=100.0, last_line_type="assistant", now=101.0) == STATE_WORKING
    assert compute_state(last_mtime=100.0, last_line_type="user", now=101.5) == STATE_WORKING


def test_waiting_when_assistant_is_last_and_recent_but_not_active() -> None:
    # 10 seconds since last write
    assert compute_state(last_mtime=100.0, last_line_type="assistant", now=110.0) == STATE_WAITING


def test_waiting_when_assistant_is_last_and_within_five_minutes() -> None:
    assert compute_state(last_mtime=100.0, last_line_type="assistant", now=100.0 + 4 * 60) == STATE_WAITING


def test_idle_when_more_than_five_minutes_since_last_write() -> None:
    assert compute_state(last_mtime=100.0, last_line_type="assistant", now=100.0 + 6 * 60) == STATE_IDLE


def test_idle_when_last_line_is_not_assistant_after_two_seconds() -> None:
    assert compute_state(last_mtime=100.0, last_line_type="user", now=110.0) == STATE_IDLE
    assert compute_state(last_mtime=100.0, last_line_type=None, now=110.0) == STATE_IDLE


def test_read_last_complete_line_type_ignores_partial_tail(tmp_path: Path) -> None:
    path = tmp_path / "s.jsonl"
    complete = json.dumps({"type": "assistant", "message": {}})
    partial = '{"type": "user"'  # no closing brace, no trailing newline
    path.write_text(complete + "\n" + partial)

    assert read_last_complete_line_type(path) == "assistant"


def test_read_last_complete_line_type_returns_none_on_empty(tmp_path: Path) -> None:
    path = tmp_path / "s.jsonl"
    path.write_text("")

    assert read_last_complete_line_type(path) is None


def test_read_last_complete_line_type_returns_none_on_missing_file(tmp_path: Path) -> None:
    assert read_last_complete_line_type(tmp_path / "nope.jsonl") is None


def test_read_last_complete_line_type_with_trailing_newline(tmp_path: Path) -> None:
    path = tmp_path / "s.jsonl"
    _write(path, [
        {"type": "user"},
        {"type": "assistant"},
    ])

    assert read_last_complete_line_type(path) == "assistant"
