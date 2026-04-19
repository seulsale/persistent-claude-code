import json
from pathlib import Path

from persistent_claude_code.sessions import (
    Project,
    Session,
    decode_project_dir,
    parse_session_metadata,
    resolve_project_cwd,
)


def test_decode_dir_simple() -> None:
    # Encoding is lossy: every '-' after the leading one becomes '/'.
    # Authoritative path resolution happens in resolve_project_cwd (Task 4).
    assert decode_project_dir("-home-seulsale-dev-ai-learn") == "/home/seulsale/dev/ai/learn"


def test_decode_dir_with_leading_dash_only() -> None:
    assert decode_project_dir("-tmp") == "/tmp"


def test_decode_dir_without_leading_dash_returned_as_is() -> None:
    assert decode_project_dir("weird") == "weird"


def test_project_dataclass_defaults() -> None:
    p = Project(path="/tmp", exists=True)
    assert p.sessions == []


def test_session_dataclass_fields() -> None:
    s = Session(
        id="abc",
        project_path="/tmp",
        title="hello",
        branch="main",
        last_activity=1700000000.0,
        jsonl_path=Path("/tmp/abc.jsonl"),
    )
    assert s.id == "abc"
    assert s.jsonl_path.name == "abc.jsonl"


def _write_jsonl(path: Path, lines: list[dict]) -> None:
    path.write_text("\n".join(json.dumps(line) for line in lines) + "\n")


def test_parse_metadata_uses_last_prompt_entry(tmp_path: Path) -> None:
    path = tmp_path / "s.jsonl"
    _write_jsonl(path, [
        {"type": "user", "message": {"role": "user", "content": "first prompt"}, "gitBranch": "main"},
        {"type": "assistant", "message": {}, "gitBranch": "main"},
        {"type": "last-prompt", "lastPrompt": "most recent prompt", "sessionId": "s"},
    ])

    meta = parse_session_metadata(path)

    assert meta.title == "most recent prompt"
    assert meta.branch == "main"


def test_parse_metadata_falls_back_to_first_user_message(tmp_path: Path) -> None:
    path = tmp_path / "s.jsonl"
    _write_jsonl(path, [
        {"type": "user", "message": {"role": "user", "content": "opening prompt text"}},
        {"type": "assistant", "message": {}},
    ])

    meta = parse_session_metadata(path)

    assert meta.title == "opening prompt text"


def test_parse_metadata_handles_string_content(tmp_path: Path) -> None:
    path = tmp_path / "s.jsonl"
    _write_jsonl(path, [
        {"type": "user", "message": {"role": "user", "content": [{"type": "text", "text": "from array"}]}},
    ])

    meta = parse_session_metadata(path)

    assert meta.title == "from array"


def test_parse_metadata_untitled_when_no_user_messages(tmp_path: Path) -> None:
    path = tmp_path / "s.jsonl"
    _write_jsonl(path, [
        {"type": "permission-mode", "permissionMode": "default"},
    ])

    meta = parse_session_metadata(path)

    assert meta.title == "Untitled session"
    assert meta.branch is None


def test_parse_metadata_ignores_sidechain_messages(tmp_path: Path) -> None:
    path = tmp_path / "s.jsonl"
    _write_jsonl(path, [
        {"type": "user", "isSidechain": True, "message": {"content": "subagent prompt"}},
        {"type": "user", "isSidechain": False, "message": {"content": "main prompt"}},
    ])

    meta = parse_session_metadata(path)

    assert meta.title == "main prompt"


def test_parse_metadata_tail_reads_only_last_window(tmp_path: Path) -> None:
    # file larger than the 200 KB window: ensure we still find last-prompt at end
    path = tmp_path / "big.jsonl"
    padding = [{"type": "attachment", "data": "x" * 1024} for _ in range(300)]
    padding.append({"type": "last-prompt", "lastPrompt": "tail prompt", "sessionId": "s"})
    _write_jsonl(path, padding)

    meta = parse_session_metadata(path)

    assert meta.title == "tail prompt"


def test_resolve_project_cwd_prefers_cwd_field(tmp_path: Path) -> None:
    subdir = tmp_path / "-home-user-myproj"
    subdir.mkdir()
    _write_jsonl(subdir / "abc.jsonl", [
        {"type": "user", "cwd": "/home/user/myproj", "message": {"content": "hi"}},
    ])

    path, exists = resolve_project_cwd(subdir)

    assert path == "/home/user/myproj"
    assert exists is False  # the path doesn't actually exist on disk
