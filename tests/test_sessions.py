from pathlib import Path

from persistent_claude_code.sessions import Project, Session, decode_project_dir


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
