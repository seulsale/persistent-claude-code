import stat
from pathlib import Path

from persistent_claude_code.claude_binary import resolve_claude_binary


def _make_executable(path: Path) -> None:
    path.write_text("#!/bin/sh\nexit 0\n")
    path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def test_override_returns_when_file(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("PATH", "/nonexistent")
    binary = tmp_path / "claude"
    _make_executable(binary)
    assert resolve_claude_binary(str(binary)) == str(binary)


def test_override_returns_none_when_missing(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("PATH", "/nonexistent")
    assert resolve_claude_binary(str(tmp_path / "nope")) is None


def test_uses_path_when_available(tmp_path: Path, monkeypatch) -> None:
    binary = tmp_path / "claude"
    _make_executable(binary)
    monkeypatch.setenv("PATH", str(tmp_path))
    monkeypatch.setenv("HOME", str(tmp_path / "empty-home"))
    assert resolve_claude_binary(None) == str(binary)


def test_falls_back_to_local_bin_when_not_on_path(tmp_path: Path, monkeypatch) -> None:
    local_bin = tmp_path / ".local" / "bin"
    local_bin.mkdir(parents=True)
    binary = local_bin / "claude"
    _make_executable(binary)

    monkeypatch.setenv("PATH", "/nonexistent")
    monkeypatch.setenv("HOME", str(tmp_path))

    assert resolve_claude_binary(None) == str(binary)


def test_returns_none_when_truly_missing(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(
        "persistent_claude_code.claude_binary._FALLBACK_PATHS",
        [str(tmp_path / "nope-1"), str(tmp_path / "nope-2")],
    )
    monkeypatch.setenv("PATH", "/nonexistent")
    monkeypatch.setenv("HOME", str(tmp_path))
    assert resolve_claude_binary(None) is None
