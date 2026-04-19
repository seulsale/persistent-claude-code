import json
import os
from pathlib import Path

from persistent_claude_code.sessions import (
    Project,
    Session,
    decode_project_dir,
    filter_sessions,
    parse_session_metadata,
    resolve_project_cwd,
    scan_projects,
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


def _make_session_dir(tmp_path: Path, dir_name: str, cwd: str, sessions: list[tuple[str, str]]) -> Path:
    subdir = tmp_path / dir_name
    subdir.mkdir()
    for sid, title in sessions:
        path = subdir / f"{sid}.jsonl"
        _write_jsonl(path, [
            {"type": "user", "cwd": cwd, "gitBranch": "main", "message": {"content": title}},
            {"type": "last-prompt", "lastPrompt": title, "sessionId": sid},
        ])
    return subdir


def test_scan_projects_groups_sessions(tmp_path: Path) -> None:
    _make_session_dir(tmp_path, "-a", "/tmp/a", [("s1", "first"), ("s2", "second")])
    _make_session_dir(tmp_path, "-b", "/tmp/b", [("s3", "third")])

    model = scan_projects(tmp_path)

    paths = {p.path for p in model.projects}
    assert paths == {"/tmp/a", "/tmp/b"}
    proj_a = next(p for p in model.projects if p.path == "/tmp/a")
    assert {s.id for s in proj_a.sessions} == {"s1", "s2"}


def test_scan_orders_projects_by_recency(tmp_path: Path) -> None:
    older = _make_session_dir(tmp_path, "-old", "/tmp/old", [("o1", "old")])
    newer = _make_session_dir(tmp_path, "-new", "/tmp/new", [("n1", "new")])
    os.utime(older / "o1.jsonl", (1_000_000_000, 1_000_000_000))
    os.utime(newer / "n1.jsonl", (1_700_000_000, 1_700_000_000))

    model = scan_projects(tmp_path)

    assert [p.path for p in model.projects] == ["/tmp/new", "/tmp/old"]


def test_scan_orders_sessions_newest_first(tmp_path: Path) -> None:
    subdir = _make_session_dir(tmp_path, "-p", "/tmp/p", [("older", "o"), ("newer", "n")])
    os.utime(subdir / "older.jsonl", (1_000_000_000, 1_000_000_000))
    os.utime(subdir / "newer.jsonl", (1_700_000_000, 1_700_000_000))

    model = scan_projects(tmp_path)

    session_ids = [s.id for s in model.projects[0].sessions]
    assert session_ids == ["newer", "older"]


def test_scan_skips_non_jsonl_and_empty_subdirs(tmp_path: Path) -> None:
    (tmp_path / "-empty").mkdir()
    _make_session_dir(tmp_path, "-p", "/tmp/p", [("s1", "hi")])
    (tmp_path / "-p" / "notes.txt").write_text("ignore me")

    model = scan_projects(tmp_path)

    paths = {p.path for p in model.projects}
    assert paths == {"/tmp/p"}


def test_filter_empty_query_returns_model_unchanged(tmp_path: Path) -> None:
    _make_session_dir(tmp_path, "-a", "/tmp/a", [("s1", "one"), ("s2", "two")])
    model = scan_projects(tmp_path)

    filtered = filter_sessions("", model)

    assert filtered == model


def test_filter_matches_session_title(tmp_path: Path) -> None:
    _make_session_dir(tmp_path, "-a", "/tmp/a", [("s1", "fix login bug"), ("s2", "refactor router")])
    model = scan_projects(tmp_path)

    filtered = filter_sessions("login", model)

    assert len(filtered.projects) == 1
    assert [s.id for s in filtered.projects[0].sessions] == ["s1"]


def test_filter_matches_project_path(tmp_path: Path) -> None:
    _make_session_dir(tmp_path, "-a", "/tmp/ayzer-dental", [("s1", "x")])
    _make_session_dir(tmp_path, "-b", "/tmp/qanto", [("s2", "y")])
    model = scan_projects(tmp_path)

    filtered = filter_sessions("ayzer", model)

    assert [p.path for p in filtered.projects] == ["/tmp/ayzer-dental"]


def test_filter_is_case_insensitive(tmp_path: Path) -> None:
    _make_session_dir(tmp_path, "-a", "/tmp/a", [("s1", "FIX Login BUG")])
    model = scan_projects(tmp_path)

    filtered = filter_sessions("login", model)

    assert len(filtered.projects[0].sessions) == 1


def test_filter_drops_projects_with_no_matching_sessions(tmp_path: Path) -> None:
    _make_session_dir(tmp_path, "-match", "/tmp/match", [("s1", "hello")])
    _make_session_dir(tmp_path, "-nomatch", "/tmp/nomatch", [("s2", "nope")])
    model = scan_projects(tmp_path)

    filtered = filter_sessions("hello", model)

    assert [p.path for p in filtered.projects] == ["/tmp/match"]


def test_filter_keeps_project_when_name_matches_even_if_sessions_do_not(tmp_path: Path) -> None:
    _make_session_dir(tmp_path, "-needle", "/tmp/needle", [("s1", "unrelated title")])
    model = scan_projects(tmp_path)

    filtered = filter_sessions("needle", model)

    assert len(filtered.projects) == 1
    # when project matches by path, its sessions are preserved
    assert len(filtered.projects[0].sessions) == 1
