# Persistent Claude Code v1 — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship v0.1.0 of a GTK4/Libadwaita desktop app that browses Claude Code sessions from `~/.claude/projects/`, spawns `claude --resume` inside an embedded VTE terminal tab, optionally shows a WebKitGTK browser pane alongside each session, and displays a live status dot on sessions that are active in the app.

**Architecture:** Single Python 3.14+ process. Pure-data model (`config.py`, `sessions.py`, `status.py`) with zero GTK imports, fully unit-tested. A GTK layer (`app.py`, `sidebar.py`, `tab.py`, `terminal.py`, `browser.py`) consumes the model and is verified by running the app and observing behavior. State changes in the jsonl files are detected via `Gio.FileMonitor` and mapped through a pure function to a status enum.

**Tech Stack:** Python 3.14+, PyGObject, GTK4, Libadwaita, VTE4, WebKitGTK 6, pytest, ruff.

**Spec:** `docs/superpowers/specs/2026-04-18-persistent-claude-code-v1-design.md`

**Conventions:**
- Commit after every passing task. Use `feat:`, `test:`, `chore:`, `docs:`, `fix:` prefixes.
- Every pure-Python module has matching `tests/test_<module>.py`. GTK widgets are verified manually against documented steps.
- Never catch broad `Exception` unless immediately followed by a user-visible surface (toast/log). At boundaries, convert to typed dataclasses.
- No unused imports, no dead code, no commented-out code. `ruff check` must pass.

---

## Task 1: Project scaffolding

**Files:**
- Create: `pyproject.toml`
- Create: `src/persistent_claude_code/__init__.py`
- Create: `src/persistent_claude_code/__main__.py`
- Create: `tests/__init__.py`
- Create: `tests/conftest.py`
- Create: `Makefile`
- Create: `LICENSE`
- Modify: `.gitignore`

- [ ] **Step 1: Create `pyproject.toml`**

```toml
[project]
name = "persistent-claude-code"
version = "0.1.0"
description = "GTK desktop app for browsing and resuming Claude Code sessions"
requires-python = ">=3.14"
license = { text = "MIT" }
authors = [{ name = "seulsale" }]
dependencies = []

[project.scripts]
persistent-claude-code = "persistent_claude_code.__main__:main"

[build-system]
requires = ["setuptools>=70"]
build-backend = "setuptools.build_meta"

[tool.setuptools.packages.find]
where = ["src"]

[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "-ra --strict-markers"
pythonpath = ["src"]

[tool.ruff]
line-length = 100
src = ["src", "tests"]

[tool.ruff.lint]
select = ["E", "F", "W", "I", "UP", "B", "SIM"]
ignore = ["E501"]
```

- [ ] **Step 2: Create `src/persistent_claude_code/__init__.py`**

```python
__version__ = "0.1.0"
```

- [ ] **Step 3: Create `src/persistent_claude_code/__main__.py`**

```python
def main() -> int:
    from persistent_claude_code.main import run
    return run()


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Create `tests/__init__.py`** (empty file)

- [ ] **Step 5: Create `tests/conftest.py`**

```python
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
```

- [ ] **Step 6: Create `Makefile`**

```makefile
.PHONY: run test lint install uninstall

run:
	python3 -m persistent_claude_code

test:
	python3 -m pytest

lint:
	python3 -m ruff check

install:
	./install.sh

uninstall:
	./uninstall.sh
```

- [ ] **Step 7: Create `LICENSE`** (MIT, year 2026, owner: seulsale)

```
MIT License

Copyright (c) 2026 seulsale

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

- [ ] **Step 8: Ensure `.gitignore` covers Python + local state**

Expected `.gitignore` content:

```
.superpowers/
__pycache__/
*.pyc
.venv/
dist/
build/
*.egg-info/
.pytest_cache/
.ruff_cache/
```

(If the file already exists, add the missing lines.)

- [ ] **Step 9: Verify interpreter and test runner**

Run: `python3 --version`
Expected: `Python 3.14.x` or higher. If not, stop and install Python 3.14 before proceeding.

Run: `python3 -m pytest --version`
Expected: pytest prints its version.

Run: `python3 -m ruff --version`
Expected: ruff prints its version. (If missing: `sudo pacman -S ruff`.)

- [ ] **Step 10: Commit**

```bash
git add pyproject.toml Makefile LICENSE .gitignore src tests
git commit -m "chore: scaffold package, build config, and test harness"
```

---

## Task 2: Config module

**Files:**
- Create: `src/persistent_claude_code/config.py`
- Create: `tests/test_config.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_config.py`:

```python
import json
from pathlib import Path

from persistent_claude_code.config import Config, load, save


def test_defaults_when_no_file(tmp_path: Path) -> None:
    cfg = load(tmp_path / "config.json")
    assert cfg == Config()
    assert cfg.terminal_font == "Monospace 11"
    assert cfg.terminal_scrollback == 10000
    assert cfg.claude_binary is None
    assert cfg.browser_home == "about:blank"
    assert cfg.window_size == (1400, 900)


def test_load_reads_existing_file(tmp_path: Path) -> None:
    path = tmp_path / "config.json"
    path.write_text(json.dumps({
        "terminal_font": "Fira Mono 12",
        "window_size": [1920, 1080],
    }))

    cfg = load(path)

    assert cfg.terminal_font == "Fira Mono 12"
    assert cfg.window_size == (1920, 1080)
    assert cfg.terminal_scrollback == 10000  # default preserved


def test_save_writes_json(tmp_path: Path) -> None:
    path = tmp_path / "config.json"
    cfg = Config(terminal_font="Iosevka 10", window_size=(800, 600))

    save(cfg, path)

    written = json.loads(path.read_text())
    assert written["terminal_font"] == "Iosevka 10"
    assert written["window_size"] == [800, 600]


def test_load_ignores_unknown_keys(tmp_path: Path) -> None:
    path = tmp_path / "config.json"
    path.write_text(json.dumps({"unknown_key": "value", "terminal_font": "Foo 9"}))

    cfg = load(path)

    assert cfg.terminal_font == "Foo 9"


def test_load_recovers_from_corrupt_json(tmp_path: Path) -> None:
    path = tmp_path / "config.json"
    path.write_text("{ not json")

    cfg = load(path)

    assert cfg == Config()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_config.py -v`
Expected: FAIL — `ModuleNotFoundError` or missing `Config`.

- [ ] **Step 3: Implement `config.py`**

Create `src/persistent_claude_code/config.py`:

```python
from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field, fields
from pathlib import Path


@dataclass(frozen=True)
class Config:
    terminal_font: str = "Monospace 11"
    terminal_scrollback: int = 10000
    claude_binary: str | None = None
    browser_home: str = "about:blank"
    window_size: tuple[int, int] = field(default=(1400, 900))


def default_path() -> Path:
    base = os.environ.get("XDG_CONFIG_HOME") or str(Path.home() / ".config")
    return Path(base) / "persistent-claude-code" / "config.json"


def load(path: Path | None = None) -> Config:
    path = path or default_path()
    if not path.exists():
        return Config()
    try:
        raw = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return Config()
    if not isinstance(raw, dict):
        return Config()

    known = {f.name for f in fields(Config)}
    kwargs: dict[str, object] = {}
    for key, value in raw.items():
        if key not in known:
            continue
        if key == "window_size" and isinstance(value, list) and len(value) == 2:
            kwargs[key] = (int(value[0]), int(value[1]))
        else:
            kwargs[key] = value
    return Config(**kwargs)  # type: ignore[arg-type]


def save(cfg: Config, path: Path | None = None) -> None:
    path = path or default_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    data = asdict(cfg)
    data["window_size"] = list(cfg.window_size)
    path.write_text(json.dumps(data, indent=2))
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_config.py -v`
Expected: 5 passed.

- [ ] **Step 5: Lint**

Run: `python3 -m ruff check src/persistent_claude_code/config.py tests/test_config.py`
Expected: `All checks passed!`.

- [ ] **Step 6: Commit**

```bash
git add src/persistent_claude_code/config.py tests/test_config.py
git commit -m "feat(config): load/save JSON config with defaults and corruption recovery"
```

---

## Task 3: Sessions model — dataclasses and directory decoding

**Files:**
- Create: `src/persistent_claude_code/sessions.py`
- Create: `tests/test_sessions.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_sessions.py`:

```python
from pathlib import Path

from persistent_claude_code.sessions import Project, Session, decode_project_dir


def test_decode_dir_simple() -> None:
    assert decode_project_dir("-home-seulsale-dev-ai-learn") == "/home/seulsale/dev/ai-learn"


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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_sessions.py -v`
Expected: FAIL — missing module or names.

- [ ] **Step 3: Implement initial `sessions.py`**

Create `src/persistent_claude_code/sessions.py`:

```python
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
    if name.startswith("-"):
        return "/" + name[1:].replace("-", "/")
    return name
```

- [ ] **Step 4: Run tests**

Run: `python3 -m pytest tests/test_sessions.py -v`
Expected: 5 passed.

- [ ] **Step 5: Commit**

```bash
git add src/persistent_claude_code/sessions.py tests/test_sessions.py
git commit -m "feat(sessions): add Session/Project/Model dataclasses and dir decoder"
```

---

## Task 4: Sessions model — jsonl tail parsing

**Files:**
- Modify: `src/persistent_claude_code/sessions.py`
- Modify: `tests/test_sessions.py`

- [ ] **Step 1: Append failing tests to `tests/test_sessions.py`**

```python
import json
from pathlib import Path

from persistent_claude_code.sessions import (
    parse_session_metadata,
    resolve_project_cwd,
)


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
```

- [ ] **Step 2: Run tests to confirm they fail**

Run: `python3 -m pytest tests/test_sessions.py -v`
Expected: FAIL — missing `parse_session_metadata`, `resolve_project_cwd`.

- [ ] **Step 3: Extend `sessions.py`**

Append to `src/persistent_claude_code/sessions.py`:

```python
import json
import os
from dataclasses import dataclass as _dc

TAIL_BYTES = 200 * 1024
UNTITLED = "Untitled session"


@_dc
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
```

- [ ] **Step 4: Run tests**

Run: `python3 -m pytest tests/test_sessions.py -v`
Expected: all passing.

- [ ] **Step 5: Commit**

```bash
git add src/persistent_claude_code/sessions.py tests/test_sessions.py
git commit -m "feat(sessions): parse title/branch from jsonl tail and resolve project cwd"
```

---

## Task 5: Sessions model — scan and filter

**Files:**
- Modify: `src/persistent_claude_code/sessions.py`
- Modify: `tests/test_sessions.py`

- [ ] **Step 1: Append failing tests**

Add to `tests/test_sessions.py`:

```python
from persistent_claude_code.sessions import Model, filter_sessions, scan_projects


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
    import os
    os.utime(older / "o1.jsonl", (1_000_000_000, 1_000_000_000))
    os.utime(newer / "n1.jsonl", (1_700_000_000, 1_700_000_000))

    model = scan_projects(tmp_path)

    assert [p.path for p in model.projects] == ["/tmp/new", "/tmp/old"]


def test_scan_orders_sessions_newest_first(tmp_path: Path) -> None:
    subdir = _make_session_dir(tmp_path, "-p", "/tmp/p", [("older", "o"), ("newer", "n")])
    import os
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
```

- [ ] **Step 2: Run tests to confirm they fail**

Run: `python3 -m pytest tests/test_sessions.py -v`
Expected: multiple FAIL — missing `scan_projects`, `filter_sessions`.

- [ ] **Step 3: Extend `sessions.py`**

Append to `src/persistent_claude_code/sessions.py`:

```python
def scan_projects(root: Path) -> Model:
    if not root.is_dir():
        return Model(projects=[])

    projects: list[Project] = []
    for subdir in sorted(root.iterdir()):
        if not subdir.is_dir():
            continue
        jsonls = sorted(subdir.glob("*.jsonl"))
        if not jsonls:
            continue

        project_path, exists = resolve_project_cwd(subdir)

        sessions: list[Session] = []
        for jsonl in jsonls:
            meta = parse_session_metadata(jsonl)
            sessions.append(Session(
                id=jsonl.stem,
                project_path=project_path,
                title=meta.title,
                branch=meta.branch,
                last_activity=jsonl.stat().st_mtime,
                jsonl_path=jsonl,
            ))
        sessions.sort(key=lambda s: s.last_activity, reverse=True)
        projects.append(Project(path=project_path, exists=exists, sessions=sessions))

    projects.sort(
        key=lambda p: max((s.last_activity for s in p.sessions), default=0.0),
        reverse=True,
    )
    return Model(projects=projects)


def filter_sessions(query: str, model: Model) -> Model:
    query = query.strip().lower()
    if not query:
        return model

    result: list[Project] = []
    for project in model.projects:
        project_matches = query in project.path.lower()
        if project_matches:
            # keep all sessions in a matching project
            result.append(Project(path=project.path, exists=project.exists, sessions=list(project.sessions)))
            continue

        matching_sessions = [s for s in project.sessions if query in s.title.lower()]
        if matching_sessions:
            result.append(Project(path=project.path, exists=project.exists, sessions=matching_sessions))

    return Model(projects=result)
```

- [ ] **Step 4: Run tests**

Run: `python3 -m pytest tests/test_sessions.py -v`
Expected: all passing (16+ tests total in the file).

- [ ] **Step 5: Lint**

Run: `python3 -m ruff check src/persistent_claude_code/sessions.py tests/test_sessions.py`
Expected: clean.

- [ ] **Step 6: Commit**

```bash
git add src/persistent_claude_code/sessions.py tests/test_sessions.py
git commit -m "feat(sessions): scan project dirs and filter model by query"
```

---

## Task 6: Status module — state machine

**Files:**
- Create: `src/persistent_claude_code/status.py`
- Create: `tests/test_status.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_status.py`:

```python
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
```

- [ ] **Step 2: Run to confirm failure**

Run: `python3 -m pytest tests/test_status.py -v`
Expected: FAIL — missing module.

- [ ] **Step 3: Implement `status.py`**

Create `src/persistent_claude_code/status.py`:

```python
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
```

- [ ] **Step 4: Run tests**

Run: `python3 -m pytest tests/test_status.py -v`
Expected: 9 passed.

- [ ] **Step 5: Lint**

Run: `python3 -m ruff check src/persistent_claude_code/status.py tests/test_status.py`
Expected: clean.

- [ ] **Step 6: Commit**

```bash
git add src/persistent_claude_code/status.py tests/test_status.py
git commit -m "feat(status): pure state machine and tail-parser for session jsonl"
```

---

## Task 7: GTK application skeleton

**Files:**
- Create: `src/persistent_claude_code/main.py`
- Create: `src/persistent_claude_code/app.py`

- [ ] **Step 1: Create `main.py`**

```python
from __future__ import annotations

import sys


def run() -> int:
    import gi
    gi.require_version("Gtk", "4.0")
    gi.require_version("Adw", "1")
    gi.require_version("Vte", "3.91")
    gi.require_version("WebKit", "6.0")

    from persistent_claude_code.app import App

    app = App()
    return app.run(sys.argv)
```

- [ ] **Step 2: Create `app.py` with minimal Adw.Application + window**

```python
from __future__ import annotations

from gi.repository import Adw, Gio, Gtk

from persistent_claude_code import __version__
from persistent_claude_code.config import Config, load as load_config, save as save_config

APP_ID = "io.github.seulsale.PersistentClaudeCode"
APP_NAME = "Persistent Claude Code"


class MainWindow(Adw.ApplicationWindow):
    def __init__(self, app: "App") -> None:
        super().__init__(application=app, title=APP_NAME)
        self._app = app
        w, h = app.config.window_size
        self.set_default_size(w, h)

        placeholder = Adw.StatusPage(
            icon_name="document-open-symbolic",
            title="Persistent Claude Code",
            description="Pick a session from the sidebar, or start a new one.",
        )

        header = Adw.HeaderBar()
        toolbar = Adw.ToolbarView()
        toolbar.add_top_bar(header)
        toolbar.set_content(placeholder)
        self.set_content(toolbar)

        self.connect("close-request", self._on_close_request)

    def _on_close_request(self, *_a: object) -> bool:
        w = self.get_width()
        h = self.get_height()
        self._app.config = Config(
            terminal_font=self._app.config.terminal_font,
            terminal_scrollback=self._app.config.terminal_scrollback,
            claude_binary=self._app.config.claude_binary,
            browser_home=self._app.config.browser_home,
            window_size=(w, h),
        )
        save_config(self._app.config)
        return False


class App(Adw.Application):
    def __init__(self) -> None:
        super().__init__(
            application_id=APP_ID,
            flags=Gio.ApplicationFlags.DEFAULT_FLAGS,
        )
        self.config: Config = load_config()
        self._window: MainWindow | None = None

    def do_activate(self) -> None:
        if self._window is None:
            self._window = MainWindow(self)
        self._window.present()
```

- [ ] **Step 3: Launch once to verify the app opens**

Run: `make run`
Expected: a GTK window titled "Persistent Claude Code" appears with the "Pick a session..." status page, 1400×900. Close it; a fresh `~/.config/persistent-claude-code/config.json` should now exist.

Run: `cat ~/.config/persistent-claude-code/config.json`
Expected: JSON with the default keys.

- [ ] **Step 4: Commit**

```bash
git add src/persistent_claude_code/main.py src/persistent_claude_code/app.py
git commit -m "feat(app): Adw.Application skeleton with window and config persistence"
```

---

## Task 8: Sidebar — projects tree widget (without live status)

**Files:**
- Create: `src/persistent_claude_code/sidebar.py`
- Modify: `src/persistent_claude_code/app.py`

- [ ] **Step 1: Create `sidebar.py`**

```python
from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path

from gi.repository import Gio, GLib, GObject, Gtk

from persistent_claude_code.sessions import Model, Project, Session, filter_sessions, scan_projects

CLAUDE_PROJECTS_DIR = Path.home() / ".claude" / "projects"

OnOpenSession = Callable[[Session], None]
OnNewSession = Callable[[Project], None]


def _relative_time(ts: float) -> str:
    now = datetime.now(tz=timezone.utc).timestamp()
    d = int(now - ts)
    if d < 60:
        return f"{d}s ago"
    if d < 3600:
        return f"{d // 60}m ago"
    if d < 86400:
        return f"{d // 3600}h ago"
    return f"{d // 86400}d ago"


class _SessionRow(Gtk.ListBoxRow):
    __gtype_name__ = "PCCSessionRow"

    def __init__(self, session: Session) -> None:
        super().__init__()
        self.session = session
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2, margin_top=4, margin_bottom=4, margin_start=8, margin_end=8)
        title = Gtk.Label(label=session.title, xalign=0, ellipsize=3, max_width_chars=40)
        title.add_css_class("heading")
        meta_text = _relative_time(session.last_activity)
        if session.branch:
            meta_text = f"{meta_text} · {session.branch}"
        meta = Gtk.Label(label=meta_text, xalign=0)
        meta.add_css_class("dim-label")
        meta.add_css_class("caption")

        header_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self.status_dot = Gtk.Image.new_from_icon_name("")
        self.status_dot.set_pixel_size(10)
        self.status_dot.set_visible(False)
        header_box.append(title)
        header_box.append(Gtk.Box(hexpand=True))
        header_box.append(self.status_dot)

        box.append(header_box)
        box.append(meta)
        self.set_child(box)


class _NewSessionRow(Gtk.ListBoxRow):
    __gtype_name__ = "PCCNewSessionRow"

    def __init__(self, project: Project) -> None:
        super().__init__()
        self.project = project
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6, margin_top=4, margin_bottom=4, margin_start=8, margin_end=8)
        box.append(Gtk.Image.new_from_icon_name("list-add-symbolic"))
        label = Gtk.Label(label="New session", xalign=0)
        label.add_css_class("heading")
        box.append(label)
        self.set_child(box)


class Sidebar(Gtk.Box):
    __gtype_name__ = "PCCSidebar"

    def __init__(self, on_open: OnOpenSession, on_new: OnNewSession) -> None:
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self._on_open = on_open
        self._on_new = on_new

        self.search = Gtk.SearchEntry(placeholder_text="Filter sessions (Ctrl+K)")
        self.search.connect("search-changed", self._on_search_changed)
        self.search.connect("activate", self._on_search_activate)

        search_wrap = Gtk.Box(margin_top=6, margin_bottom=6, margin_start=8, margin_end=8)
        search_wrap.append(self.search)
        self.search.set_hexpand(True)
        self.append(search_wrap)

        self._tree = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        scrolled = Gtk.ScrolledWindow(hscrollbar_policy=Gtk.PolicyType.NEVER, vexpand=True)
        scrolled.set_child(self._tree)
        self.append(scrolled)

        self._model = Model()
        self._rows: dict[str, _SessionRow] = {}

        self._monitor: Gio.FileMonitor | None = None

    def refresh(self) -> None:
        self._model = scan_projects(CLAUDE_PROJECTS_DIR)
        self._rebuild()

    def start_watching(self) -> None:
        if self._monitor is not None:
            return
        CLAUDE_PROJECTS_DIR.mkdir(parents=True, exist_ok=True)
        gio_dir = Gio.File.new_for_path(str(CLAUDE_PROJECTS_DIR))
        self._monitor = gio_dir.monitor_directory(Gio.FileMonitorFlags.WATCH_MOVES, None)
        self._monitor.connect("changed", self._on_fs_changed)

    def _on_fs_changed(self, *_a: object) -> None:
        # Debounce: schedule a refresh on next idle; multiple events coalesce.
        GLib.idle_add(self._debounced_refresh)

    def _debounced_refresh(self) -> bool:
        self.refresh()
        return False

    def get_row_for_session(self, session_id: str) -> _SessionRow | None:
        return self._rows.get(session_id)

    def _rebuild(self) -> None:
        child = self._tree.get_first_child()
        while child is not None:
            self._tree.remove(child)
            child = self._tree.get_first_child()
        self._rows = {}

        query = self.search.get_text()
        visible = filter_sessions(query, self._model)

        for project in visible.projects:
            expander = Gtk.Expander(label=_project_label(project), expanded=True)
            expander.set_margin_start(4)
            expander.set_margin_end(4)
            if not project.exists:
                expander.set_tooltip_text(f"{project.path} (directory does not exist)")
                expander.add_css_class("dim-label")
            else:
                expander.set_tooltip_text(project.path)

            listbox = Gtk.ListBox()
            listbox.set_selection_mode(Gtk.SelectionMode.NONE)
            listbox.add_css_class("navigation-sidebar")
            listbox.connect("row-activated", self._on_row_activated)

            new_row = _NewSessionRow(project)
            listbox.append(new_row)

            for s in project.sessions:
                row = _SessionRow(s)
                self._rows[s.id] = row
                listbox.append(row)

            expander.set_child(listbox)
            self._tree.append(expander)

    def _on_row_activated(self, _box: Gtk.ListBox, row: Gtk.ListBoxRow) -> None:
        if isinstance(row, _SessionRow):
            self._on_open(row.session)
        elif isinstance(row, _NewSessionRow):
            self._on_new(row.project)

    def _on_search_changed(self, _entry: Gtk.SearchEntry) -> None:
        self._rebuild()

    def _on_search_activate(self, _entry: Gtk.SearchEntry) -> None:
        # Launch the first visible session, if any.
        query = self.search.get_text()
        visible = filter_sessions(query, self._model)
        for project in visible.projects:
            if project.sessions:
                self._on_open(project.sessions[0])
                return


def _project_label(project: Project) -> str:
    base = Path(project.path).name or project.path
    return base
```

- [ ] **Step 2: Wire the sidebar into `app.py`**

Replace the body of `MainWindow.__init__` in `src/persistent_claude_code/app.py` with:

```python
        super().__init__(application=app, title=APP_NAME)
        self._app = app
        w, h = app.config.window_size
        self.set_default_size(w, h)

        header = Adw.HeaderBar()

        placeholder = Adw.StatusPage(
            icon_name="document-open-symbolic",
            title="Persistent Claude Code",
            description="Pick a session from the sidebar, or start a new one.",
        )

        main_toolbar = Adw.ToolbarView()
        main_toolbar.add_top_bar(Adw.HeaderBar())
        main_toolbar.set_content(placeholder)

        from persistent_claude_code.sidebar import Sidebar

        self.sidebar = Sidebar(on_open=self._on_open_session, on_new=self._on_new_session)
        self.sidebar.refresh()
        self.sidebar.start_watching()

        sidebar_toolbar = Adw.ToolbarView()
        sidebar_toolbar.add_top_bar(header)
        sidebar_toolbar.set_content(self.sidebar)

        split = Adw.OverlaySplitView()
        split.set_sidebar(sidebar_toolbar)
        split.set_content(main_toolbar)
        split.set_show_sidebar(True)
        split.set_min_sidebar_width(260)
        split.set_sidebar_width_fraction(0.25)
        self.set_content(split)

        self.connect("close-request", self._on_close_request)
```

Add placeholder handlers to `MainWindow`:

```python
    def _on_open_session(self, session) -> None:  # Session
        print(f"(todo) open session {session.id} in {session.project_path}")

    def _on_new_session(self, project) -> None:  # Project
        print(f"(todo) new session in {project.path}")
```

- [ ] **Step 3: Launch and verify**

Run: `make run`

Expected:
- Sidebar on the left, search entry at top, list of your actual projects as expanders.
- Each project shows a `+ New session` row at the top and your real sessions below.
- Clicking a session prints `(todo) open session ...` in the terminal running make run.
- Typing in the search box narrows the tree.
- Pressing Enter in the search box launches the first visible session (prints todo).

- [ ] **Step 4: Commit**

```bash
git add src/persistent_claude_code/sidebar.py src/persistent_claude_code/app.py
git commit -m "feat(sidebar): projects tree, search, row activation wired up"
```

---

## Task 9: Terminal widget

**Files:**
- Create: `src/persistent_claude_code/terminal.py`

- [ ] **Step 1: Create `terminal.py`**

```python
from __future__ import annotations

import shutil
from collections.abc import Callable
from pathlib import Path

from gi.repository import GLib, Gtk, Vte

OnExited = Callable[[int], None]


def resolve_claude_binary(override: str | None) -> str | None:
    if override:
        return override if Path(override).is_file() else None
    return shutil.which("claude")


class TerminalPane(Gtk.Box):
    __gtype_name__ = "PCCTerminalPane"

    def __init__(self, font: str, scrollback: int, on_exited: OnExited | None = None) -> None:
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self._on_exited = on_exited

        self._stack = Gtk.Stack()
        self._stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)

        self.terminal = Vte.Terminal()
        self.terminal.set_scrollback_lines(scrollback)
        self.terminal.set_scroll_on_output(True)
        self.terminal.set_scroll_on_keystroke(True)
        font_desc = _font_description(font)
        if font_desc is not None:
            self.terminal.set_font(font_desc)
        self.terminal.connect("child-exited", self._on_child_exited)

        self._stack.add_named(self.terminal, "terminal")

        self._ended_box = self._build_ended_box()
        self._stack.add_named(self._ended_box, "ended")

        self.append(self._stack)
        self._stack.set_visible_child_name("terminal")

        self._last_argv: list[str] | None = None
        self._last_cwd: str | None = None
        self._last_exit_code: int = 0
        self._session_id: str | None = None
        self._on_resume_callback: Callable[[], None] | None = None

    def spawn(self, argv: list[str], cwd: str) -> None:
        self._last_argv = argv
        self._last_cwd = cwd
        self._stack.set_visible_child_name("terminal")
        self._ended_title.set_label("Session ended")
        self._ended_detail.set_label("")

        self.terminal.spawn_async(
            Vte.PtyFlags.DEFAULT,
            cwd,
            argv,
            None,  # envv (inherit)
            GLib.SpawnFlags.DEFAULT,
            None, None,  # child setup
            -1,   # timeout
            None, # cancellable
            None, # callback
        )

    def set_session_context(self, session_id: str | None, on_resume: Callable[[], None] | None) -> None:
        self._session_id = session_id
        self._on_resume_callback = on_resume

    def _on_child_exited(self, _term: Vte.Terminal, exit_code: int) -> None:
        self._last_exit_code = exit_code
        sid = self._session_id or ""
        detail = f"session id: {sid}" if sid else ""
        if exit_code != 0:
            detail = (detail + ("\n" if detail else "")) + f"exited with code {exit_code}"
        self._ended_detail.set_label(detail)
        self._resume_button.set_visible(self._on_resume_callback is not None)
        self._stack.set_visible_child_name("ended")
        if self._on_exited is not None:
            self._on_exited(exit_code)

    def _build_ended_box(self) -> Gtk.Widget:
        page = _EndedCardWidgets()
        self._ended_title = page.title_label
        self._ended_detail = page.detail_label
        self._resume_button = page.resume_button
        self._close_button = page.close_button

        self._resume_button.connect("clicked", self._on_resume_clicked)
        self._close_button.connect("clicked", self._on_close_clicked)
        return page.root

    def _on_resume_clicked(self, _btn: Gtk.Button) -> None:
        if self._on_resume_callback is not None:
            self._on_resume_callback()

    # Close is handled by the parent tab wiring a handler on self._close_button.


def _font_description(font_string: str):
    try:
        from gi.repository import Pango
        return Pango.FontDescription.from_string(font_string)
    except Exception:
        return None


class _EndedCardWidgets:
    """A centered card with title + detail + Resume/Close buttons."""

    def __init__(self) -> None:
        self.root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, halign=Gtk.Align.CENTER, valign=Gtk.Align.CENTER, spacing=12, margin_top=24, margin_bottom=24, margin_start=24, margin_end=24)
        self.title_label = Gtk.Label(label="Session ended")
        self.title_label.add_css_class("title-2")
        self.detail_label = Gtk.Label(label="")
        self.detail_label.add_css_class("dim-label")
        self.detail_label.set_justify(Gtk.Justification.CENTER)

        self.resume_button = Gtk.Button(label="Resume")
        self.resume_button.add_css_class("suggested-action")
        self.close_button = Gtk.Button(label="Close")

        btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8, halign=Gtk.Align.CENTER)
        btn_box.append(self.resume_button)
        btn_box.append(self.close_button)

        self.root.append(self.title_label)
        self.root.append(self.detail_label)
        self.root.append(btn_box)
```

Note: `_EndedCardWidgets` is a lightweight builder for the "ended" card; keeping the terminal module self-contained avoids leaking Adwaita into VTE-specific logic.

- [ ] **Step 2: Smoke-test by wiring a terminal into a throwaway window**

Run:

```bash
python3 - <<'PY'
import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
gi.require_version("Vte", "3.91")
from gi.repository import Adw, Gtk

from persistent_claude_code.terminal import TerminalPane

class Smoke(Adw.Application):
    def do_activate(self):
        win = Adw.ApplicationWindow(application=self, default_width=900, default_height=600)
        pane = TerminalPane("Monospace 11", 2000, on_exited=lambda c: print("exited", c))
        pane.set_session_context(session_id="smoke", on_resume=lambda: pane.spawn(["bash", "-lc", "echo hello && sleep 1"], "/tmp"))
        pane.spawn(["bash", "-lc", "echo hello && sleep 2 && exit 0"], "/tmp")
        win.set_content(pane)
        win.present()

Smoke(application_id="io.github.seulsale.pcc.smoke").run([])
PY
```

Expected:
- Terminal window appears, prints `hello`, waits 2s, then shows the "Session ended" placeholder with a **Resume** and **Close** button.
- Clicking Resume reruns the command; you see `hello` again and the ended card returns.
- Clicking Close currently does nothing (will be wired to tab close in a later task).

- [ ] **Step 3: Commit**

```bash
git add src/persistent_claude_code/terminal.py
git commit -m "feat(terminal): VTE pane with session-ended placeholder and resume"
```

---

## Task 10: Browser widget

**Files:**
- Create: `src/persistent_claude_code/browser.py`

- [ ] **Step 1: Create `browser.py`**

```python
from __future__ import annotations

from gi.repository import Gtk, WebKit


class BrowserPane(Gtk.Box):
    __gtype_name__ = "PCCBrowserPane"

    def __init__(self, home_url: str) -> None:
        super().__init__(orientation=Gtk.Orientation.VERTICAL)

        self._home_url = home_url

        toolbar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4, margin_top=4, margin_bottom=4, margin_start=4, margin_end=4)

        self._back = Gtk.Button.new_from_icon_name("go-previous-symbolic")
        self._forward = Gtk.Button.new_from_icon_name("go-next-symbolic")
        self._reload = Gtk.Button.new_from_icon_name("view-refresh-symbolic")
        self._url_entry = Gtk.Entry(hexpand=True)
        self._url_entry.set_placeholder_text("about:blank")

        toolbar.append(self._back)
        toolbar.append(self._forward)
        toolbar.append(self._reload)
        toolbar.append(self._url_entry)

        self.webview = WebKit.WebView()
        self.webview.set_vexpand(True)
        self.webview.load_uri(home_url)

        self.append(toolbar)
        self.append(self.webview)

        self._back.connect("clicked", lambda *_: self.webview.go_back())
        self._forward.connect("clicked", lambda *_: self.webview.go_forward())
        self._reload.connect("clicked", lambda *_: self.webview.reload())
        self._url_entry.connect("activate", self._on_url_activate)

        self.webview.connect("load-changed", self._sync_url)

    def _on_url_activate(self, entry: Gtk.Entry) -> None:
        text = entry.get_text().strip()
        if not text:
            return
        if not text.startswith(("http://", "https://", "about:", "file://")):
            text = "https://" + text
        self.webview.load_uri(text)

    def _sync_url(self, _webview, _evt) -> None:
        uri = self.webview.get_uri()
        if uri:
            self._url_entry.set_text(uri)
```

- [ ] **Step 2: Smoke-test with a throwaway window**

Run:

```bash
python3 - <<'PY'
import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
gi.require_version("WebKit", "6.0")
from gi.repository import Adw

from persistent_claude_code.browser import BrowserPane

class Smoke(Adw.Application):
    def do_activate(self):
        win = Adw.ApplicationWindow(application=self, default_width=900, default_height=700)
        win.set_content(BrowserPane("https://example.com"))
        win.present()

Smoke(application_id="io.github.seulsale.pcc.browsmoke").run([])
PY
```

Expected: window shows example.com with back/forward/reload buttons and editable URL bar; entering `wikipedia.org` and pressing Enter navigates to Wikipedia.

- [ ] **Step 3: Commit**

```bash
git add src/persistent_claude_code/browser.py
git commit -m "feat(browser): WebKit pane with URL bar and nav controls"
```

---

## Task 11: Session tab

**Files:**
- Create: `src/persistent_claude_code/tab.py`

- [ ] **Step 1: Create `tab.py`**

```python
from __future__ import annotations

from collections.abc import Callable

from gi.repository import Adw, Gtk

from persistent_claude_code.browser import BrowserPane
from persistent_claude_code.config import Config
from persistent_claude_code.terminal import TerminalPane


class SessionTab(Gtk.Box):
    __gtype_name__ = "PCCSessionTab"

    def __init__(
        self,
        *,
        config: Config,
        session_id: str | None,
        cwd: str,
        argv: list[str],
        on_close_requested: Callable[["SessionTab"], None],
    ) -> None:
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self.session_id = session_id
        self.cwd = cwd
        self._argv = argv
        self._config = config
        self._on_close_requested = on_close_requested

        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6, margin_top=4, margin_bottom=4, margin_start=6, margin_end=6)
        self._browser_toggle = Gtk.ToggleButton.new()
        self._browser_toggle.set_icon_name("web-browser-symbolic")
        self._browser_toggle.set_tooltip_text("Toggle browser pane (Ctrl+Shift+B)")
        self._browser_toggle.connect("toggled", self._on_toggle_browser)
        header.append(Gtk.Box(hexpand=True))
        header.append(self._browser_toggle)
        self.append(header)

        self.terminal = TerminalPane(
            font=config.terminal_font,
            scrollback=config.terminal_scrollback,
        )
        self.terminal.set_session_context(
            session_id=session_id,
            on_resume=self._resume,
        )
        self.terminal.spawn(argv, cwd)
        # Wire the "Close" button inside the ended card to our close path:
        self.terminal._close_button.connect("clicked", lambda *_: self._on_close_requested(self))

        self._split = Adw.OverlaySplitView()
        self._split.set_content(self.terminal)
        self._split.set_sidebar_position(Gtk.PackType.END)
        self._split.set_show_sidebar(False)
        self._split.set_min_sidebar_width(360)
        self._split.set_sidebar_width_fraction(0.5)
        self._browser: BrowserPane | None = None

        self.append(self._split)
        self._split.set_vexpand(True)

    def toggle_browser(self) -> None:
        self._browser_toggle.set_active(not self._browser_toggle.get_active())

    def _on_toggle_browser(self, btn: Gtk.ToggleButton) -> None:
        if btn.get_active():
            if self._browser is None:
                self._browser = BrowserPane(self._config.browser_home)
                self._split.set_sidebar(self._browser)
            self._split.set_show_sidebar(True)
        else:
            self._split.set_show_sidebar(False)

    def _resume(self) -> None:
        self.terminal.spawn(self._argv, self.cwd)
```

- [ ] **Step 2: Commit**

```bash
git add src/persistent_claude_code/tab.py
git commit -m "feat(tab): session tab combining terminal, toggleable browser pane"
```

---

## Task 12: Wire tabs into the main window

**Files:**
- Modify: `src/persistent_claude_code/app.py`

- [ ] **Step 1: Replace `MainWindow` body to host an `Adw.TabView`**

Replace `MainWindow` in `src/persistent_claude_code/app.py` with:

```python
class MainWindow(Adw.ApplicationWindow):
    def __init__(self, app: "App") -> None:
        super().__init__(application=app, title=APP_NAME)
        self._app = app
        w, h = app.config.window_size
        self.set_default_size(w, h)

        from persistent_claude_code.sidebar import Sidebar
        from persistent_claude_code.tab import SessionTab
        from persistent_claude_code.terminal import resolve_claude_binary

        self._SessionTab = SessionTab
        self._resolve_claude = resolve_claude_binary

        self._empty_state = Adw.StatusPage(
            icon_name="document-open-symbolic",
            title="Persistent Claude Code",
            description="Pick a session from the sidebar, or start a new one.",
        )

        self._tabs = Adw.TabView()
        self._tabs.connect("close-page", self._on_close_page)
        self._tabs.connect("notify::n-pages", self._refresh_main_content)

        self._tab_bar = Adw.TabBar()
        self._tab_bar.set_view(self._tabs)
        self._tab_bar.set_autohide(False)

        self._main_toolbar = Adw.ToolbarView()
        self._main_header = Adw.HeaderBar()
        self._main_toolbar.add_top_bar(self._main_header)
        self._main_toolbar.add_top_bar(self._tab_bar)
        self._main_toolbar.set_content(self._empty_state)

        self.sidebar = Sidebar(on_open=self._on_open_session, on_new=self._on_new_session)
        self.sidebar.refresh()
        self.sidebar.start_watching()

        sidebar_toolbar = Adw.ToolbarView()
        sidebar_toolbar.add_top_bar(Adw.HeaderBar())
        sidebar_toolbar.set_content(self.sidebar)

        split = Adw.OverlaySplitView()
        split.set_sidebar(sidebar_toolbar)
        split.set_content(self._main_toolbar)
        split.set_show_sidebar(True)
        split.set_min_sidebar_width(260)
        split.set_sidebar_width_fraction(0.25)

        self._toast_overlay = Adw.ToastOverlay()
        self._toast_overlay.set_child(split)
        self.set_content(self._toast_overlay)

        self._session_pages: dict[str, Adw.TabPage] = {}
        self.connect("close-request", self._on_close_request)

    def toast(self, text: str) -> None:
        self._toast_overlay.add_toast(Adw.Toast(title=text))

    def _refresh_main_content(self, *_a: object) -> None:
        if self._tabs.get_n_pages() == 0:
            self._main_toolbar.set_content(self._empty_state)
        else:
            # Switch once; the TabView manages its own content afterwards.
            if self._main_toolbar.get_content() is not self._tabs:
                self._main_toolbar.set_content(self._tabs)

    def _claude_argv(self, resume_id: str | None) -> list[str] | None:
        binary = self._resolve_claude(self._app.config.claude_binary)
        if binary is None:
            return None
        if resume_id is None:
            return [binary]
        return [binary, "--resume", resume_id]

    def _open_tab(self, *, title: str, tooltip: str, cwd: str, session_id: str | None, argv: list[str]) -> None:
        tab = self._SessionTab(
            config=self._app.config,
            session_id=session_id,
            cwd=cwd,
            argv=argv,
            on_close_requested=self._request_close_tab,
        )
        page = self._tabs.append(tab)
        page.set_title(title[:30])
        page.set_tooltip(tooltip)
        if session_id is not None:
            self._session_pages[session_id] = page
        self._tabs.set_selected_page(page)
        self._refresh_main_content()

    def _request_close_tab(self, tab) -> None:
        page = self._tabs.get_page(tab)
        self._tabs.close_page(page)

    def _on_close_page(self, _view: Adw.TabView, page: Adw.TabPage) -> bool:
        tab = page.get_child()
        sid = getattr(tab, "session_id", None)
        if sid and self._session_pages.get(sid) is page:
            del self._session_pages[sid]
        self._tabs.close_page_finish(page, True)
        return True  # we handled it

    def _on_open_session(self, session) -> None:
        existing = self._session_pages.get(session.id)
        if existing is not None:
            self._tabs.set_selected_page(existing)
            return

        argv = self._claude_argv(session.id)
        if argv is None:
            self.toast("claude not found — install Claude Code CLI")
            return

        if not __import__("pathlib").Path(session.project_path).is_dir():
            self.toast(f"Directory {session.project_path} doesn't exist; session may fail to resume.")

        self._open_tab(
            title=session.title,
            tooltip=f"{session.title}\nsession id: {session.id}",
            cwd=session.project_path,
            session_id=session.id,
            argv=argv,
        )

    def _on_new_session(self, project) -> None:
        argv = self._claude_argv(None)
        if argv is None:
            self.toast("claude not found — install Claude Code CLI")
            return
        import pathlib
        if not pathlib.Path(project.path).is_dir():
            self.toast(f"Directory {project.path} doesn't exist; session may fail to launch.")
        self._open_tab(
            title=f"New · {pathlib.Path(project.path).name}",
            tooltip=f"New session in {project.path}",
            cwd=project.path,
            session_id=None,
            argv=argv,
        )

    def _on_close_request(self, *_a: object) -> bool:
        w = self.get_width()
        h = self.get_height()
        self._app.config = Config(
            terminal_font=self._app.config.terminal_font,
            terminal_scrollback=self._app.config.terminal_scrollback,
            claude_binary=self._app.config.claude_binary,
            browser_home=self._app.config.browser_home,
            window_size=(w, h),
        )
        save_config(self._app.config)
        return False
```

- [ ] **Step 2: Launch and verify end-to-end**

Run: `make run`

Expected:
- Sidebar lists real projects/sessions.
- Clicking a session opens a tab running `claude --resume <id>` in that cwd. Claude's TUI appears inside the tab.
- Clicking the same session again focuses the existing tab (no duplicate).
- Clicking `+ New session` opens a fresh claude in that project.
- Clicking the browser-toggle button (globe icon at tab header) opens a WebKit pane to the right with `about:blank`.
- Typing a URL like `example.com` and pressing Enter navigates.
- Closing a tab while claude is running sends SIGTERM; claude exits; the ended card appears briefly before the tab is gone — or, if you let claude exit normally, the ended card appears with Resume / Close.
- Opening with `claude` not on `$PATH` shows a toast and no tab is created (simulate by `PATH= make run`).

- [ ] **Step 3: Commit**

```bash
git add src/persistent_claude_code/app.py
git commit -m "feat(app): tab view, open/focus sessions, new-session launch, toasts"
```

---

## Task 13: Live status monitoring

**Files:**
- Modify: `src/persistent_claude_code/status.py`
- Modify: `src/persistent_claude_code/sidebar.py`
- Modify: `src/persistent_claude_code/app.py`

- [ ] **Step 1: Add a `SessionStatusMonitor` class to `status.py`**

Append to `src/persistent_claude_code/status.py`:

```python
from collections.abc import Callable

from gi.repository import Gio, GLib  # type: ignore[import-not-found]

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
        file = Gio.File.new_for_path(str(self._path))
        self._monitor = file.monitor_file(Gio.FileMonitorFlags.NONE, None)
        self._monitor.connect("changed", self._on_change)
        self._timer_id = GLib.timeout_add_seconds(1, self._on_tick)
        self._recompute()

    def stop(self) -> None:
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
        try:
            mtime = self._path.stat().st_mtime
        except OSError:
            new_state: State | None = STATE_IDLE
        else:
            last_type = read_last_complete_line_type(self._path)
            import time as _time
            new_state = compute_state(last_mtime=mtime, last_line_type=last_type, now=_time.time())
        if new_state != self._last_state:
            self._last_state = new_state
            self._on_state(new_state)
```

- [ ] **Step 2: Add status dot rendering to `sidebar.py`**

Add to `src/persistent_claude_code/sidebar.py` (top-level):

```python
_STATE_ICON = {
    "working": ("● Working", "#33d17a"),
    "waiting": ("● Waiting for input", "#f5c211"),
    "idle":    ("● Idle", "#9a9996"),
}
```

Add a method on `Sidebar`:

```python
    def set_session_state(self, session_id: str, state: str | None) -> None:
        row = self._rows.get(session_id)
        if row is None:
            return
        if state is None:
            row.status_dot.set_visible(False)
            row.set_tooltip_text(None)
            return

        label, color = _STATE_ICON[state]
        # Use a unicode bullet as the "dot". Paint color via CSS class on the image widget.
        markup = f'<span foreground="{color}">●</span>'
        # Replace the image with a Gtk.Label for colored text (one-time swap is fine at scale).
        parent = row.status_dot.get_parent()
        if parent is not None:
            parent.remove(row.status_dot)
            dot = Gtk.Label()
            dot.set_use_markup(True)
            dot.set_markup(markup)
            row.status_dot = dot
            parent.append(dot)
        row.status_dot.set_visible(True)
        row.set_tooltip_text(label)
```

- [ ] **Step 3: Wire the monitor into the tab lifecycle in `app.py`**

In `MainWindow`:

```python
    # In __init__, after self._session_pages = {}:
        self._status_monitors: dict[str, "SessionStatusMonitor"] = {}  # type: ignore[name-defined]
```

Replace `_open_tab` to start/stop monitors:

```python
    def _open_tab(self, *, title: str, tooltip: str, cwd: str, session_id: str | None, argv: list[str]) -> None:
        from persistent_claude_code.status import SessionStatusMonitor
        from persistent_claude_code.sessions import CLAUDE_PROJECTS_DIR  # type: ignore[attr-defined]

        tab = self._SessionTab(
            config=self._app.config,
            session_id=session_id,
            cwd=cwd,
            argv=argv,
            on_close_requested=self._request_close_tab,
        )
        page = self._tabs.append(tab)
        page.set_title(title[:30])
        page.set_tooltip(tooltip)
        if session_id is not None:
            self._session_pages[session_id] = page

            # Locate the session's jsonl path from the sidebar model, if present.
            jsonl_path = self._find_jsonl_for_session(session_id)
            if jsonl_path is not None:
                mon = SessionStatusMonitor(
                    jsonl_path,
                    on_state=lambda s, sid=session_id: self.sidebar.set_session_state(sid, s),
                )
                mon.start()
                self._status_monitors[session_id] = mon

        self._tabs.set_selected_page(page)
        self._refresh_main_content()

    def _find_jsonl_for_session(self, session_id: str):
        for project in self.sidebar._model.projects:  # type: ignore[attr-defined]
            for s in project.sessions:
                if s.id == session_id:
                    return s.jsonl_path
        # It may not exist yet (new session); probe the directory lazily by polling.
        return None
```

Also handle tab close:

```python
    def _on_close_page(self, _view: Adw.TabView, page: Adw.TabPage) -> bool:
        tab = page.get_child()
        sid = getattr(tab, "session_id", None)
        if sid:
            mon = self._status_monitors.pop(sid, None)
            if mon is not None:
                mon.stop()
            if self._session_pages.get(sid) is page:
                del self._session_pages[sid]
        self._tabs.close_page_finish(page, True)
        return True
```

Expose `CLAUDE_PROJECTS_DIR` from `sessions.py` by moving its definition there (if it currently lives in `sidebar.py`). Update `sidebar.py` to import it.

Edit `src/persistent_claude_code/sessions.py`, add near the top:

```python
CLAUDE_PROJECTS_DIR = Path.home() / ".claude" / "projects"
```

Replace the definition in `sidebar.py` with:

```python
from persistent_claude_code.sessions import CLAUDE_PROJECTS_DIR  # noqa: F401
```

- [ ] **Step 4: Launch and verify**

Run: `make run`. Open a session from the sidebar. The session row should show a yellow or green dot depending on claude activity. Interact with claude — dot should go green while it streams, yellow after it finishes, and disappear when you close the tab.

- [ ] **Step 5: Commit**

```bash
git add src/persistent_claude_code/status.py src/persistent_claude_code/sidebar.py src/persistent_claude_code/app.py
git commit -m "feat(status): live session-state dots in the sidebar"
```

---

## Task 14: Keyboard shortcuts

**Files:**
- Modify: `src/persistent_claude_code/app.py`

- [ ] **Step 1: Register actions and shortcuts in `App` / `MainWindow`**

Add to `MainWindow.__init__`, after the window is assembled:

```python
        self._install_shortcuts()

    def _install_shortcuts(self) -> None:
        controller = Gtk.ShortcutController()
        controller.set_scope(Gtk.ShortcutScope.GLOBAL)

        def shortcut(accel: str, cb):
            trig = Gtk.ShortcutTrigger.parse_string(accel)
            act = Gtk.CallbackAction.new(lambda *_a, _cb=cb: (_cb(), True)[1])
            controller.add_shortcut(Gtk.Shortcut.new(trig, act))

        shortcut("<Ctrl>k", lambda: self.sidebar.search.grab_focus())
        shortcut("<Ctrl>w", self._close_current_tab)
        shortcut("<Ctrl>Tab", lambda: self._cycle_tab(1))
        shortcut("<Ctrl><Shift>Tab", lambda: self._cycle_tab(-1))
        shortcut("<Ctrl><Shift>b", self._toggle_current_browser)
        shortcut("<Ctrl>t", self._focus_new_session_of_current_project)
        shortcut("<Ctrl>question", self._show_about)

        self.add_controller(controller)

    def _current_tab(self):
        page = self._tabs.get_selected_page()
        if page is None:
            return None
        return page.get_child()

    def _close_current_tab(self) -> None:
        page = self._tabs.get_selected_page()
        if page is not None:
            self._tabs.close_page(page)

    def _cycle_tab(self, direction: int) -> None:
        n = self._tabs.get_n_pages()
        if n == 0:
            return
        current = self._tabs.get_selected_page()
        idx = self._tabs.get_page_position(current) if current else 0
        new_idx = (idx + direction) % n
        self._tabs.set_selected_page(self._tabs.get_nth_page(new_idx))

    def _toggle_current_browser(self) -> None:
        tab = self._current_tab()
        if tab is not None and hasattr(tab, "toggle_browser"):
            tab.toggle_browser()

    def _focus_new_session_of_current_project(self) -> None:
        # Expand the first project, focus its '+ New session' row.
        tree = self.sidebar._tree  # type: ignore[attr-defined]
        child = tree.get_first_child()
        while child is not None:
            if isinstance(child, Gtk.Expander):
                child.set_expanded(True)
                listbox = child.get_child()
                if isinstance(listbox, Gtk.ListBox):
                    first = listbox.get_row_at_index(0)
                    if first is not None:
                        first.grab_focus()
                return
            child = child.get_next_sibling()

    def _show_about(self) -> None:
        from persistent_claude_code import __version__
        about = Adw.AboutDialog(
            application_name=APP_NAME,
            application_icon="io.github.seulsale.PersistentClaudeCode",
            developer_name="seulsale",
            version=__version__,
            website="https://github.com/seulsale/persistent-claude-code",
            license_type=Gtk.License.MIT_X11,
        )
        about.present(self)
```

- [ ] **Step 2: Verify**

Run: `make run`. Open one or more sessions. Verify:
- `Ctrl+K` focuses search
- `Ctrl+W` closes current tab
- `Ctrl+Tab` / `Ctrl+Shift+Tab` cycle tabs
- `Ctrl+Shift+B` toggles the browser pane of the current tab
- `Ctrl+T` moves focus to the first project's "New session" row
- `Ctrl+?` opens the About dialog showing v0.1.0

- [ ] **Step 3: Commit**

```bash
git add src/persistent_claude_code/app.py
git commit -m "feat(app): global keyboard shortcuts and About dialog"
```

---

## Task 15: Desktop integration files

**Files:**
- Create: `data/io.github.seulsale.PersistentClaudeCode.desktop`
- Create: `data/io.github.seulsale.PersistentClaudeCode.svg`

- [ ] **Step 1: Create the .desktop file**

```ini
[Desktop Entry]
Name=Persistent Claude Code
Comment=Browse and resume Claude Code sessions
Exec=persistent-claude-code %U
Icon=io.github.seulsale.PersistentClaudeCode
Terminal=false
Type=Application
Categories=Development;Utility;
StartupWMClass=io.github.seulsale.PersistentClaudeCode
```

- [ ] **Step 2: Create an SVG icon**

Create a simple 256×256 SVG at `data/io.github.seulsale.PersistentClaudeCode.svg` with a terminal glyph and a "claude" orange tint. Suggested placeholder content (acceptable for v1, can be polished later):

```xml
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256">
  <rect width="256" height="256" rx="40" fill="#1e1e2e"/>
  <rect x="32" y="56" width="192" height="144" rx="16" fill="#11111b" stroke="#cba6f7" stroke-width="3"/>
  <text x="56" y="136" font-family="monospace" font-size="44" fill="#a6e3a1">&gt;_</text>
  <circle cx="200" cy="72" r="10" fill="#f38ba8"/>
</svg>
```

- [ ] **Step 3: Commit**

```bash
git add data/
git commit -m "chore(data): add .desktop file and SVG icon"
```

---

## Task 16: install.sh / uninstall.sh

**Files:**
- Create: `install.sh`
- Create: `uninstall.sh`

- [ ] **Step 1: Create `install.sh`**

```bash
#!/usr/bin/env bash
set -euo pipefail

APP_ID=io.github.seulsale.PersistentClaudeCode
APP_NAME=persistent-claude-code
PREFIX="${HOME}/.local"
SHARE="${PREFIX}/share"
BIN="${PREFIX}/bin"
REPO_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"

REQUIRED_PACMAN_PKGS=(python python-gobject gtk4 libadwaita vte4 webkitgtk-6.0)

missing=()
for pkg in "${REQUIRED_PACMAN_PKGS[@]}"; do
  if ! pacman -Qq "${pkg}" >/dev/null 2>&1; then
    missing+=("${pkg}")
  fi
done

if (( ${#missing[@]} > 0 )); then
  echo "Missing Arch packages: ${missing[*]}" >&2
  echo "Install with: sudo pacman -S ${missing[*]}" >&2
  exit 1
fi

py_version="$(python3 -c 'import sys;print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
if [[ "$(printf '%s\n3.14\n' "${py_version}" | sort -V | head -n1)" != "3.14" ]]; then
  echo "Python >= 3.14 required (found ${py_version})" >&2
  exit 1
fi

install -d "${SHARE}/${APP_NAME}"
cp -r "${REPO_ROOT}/src/persistent_claude_code" "${SHARE}/${APP_NAME}/"

install -d "${BIN}"
cat > "${BIN}/${APP_NAME}" <<EOF
#!/usr/bin/env bash
exec python3 -c 'import sys; sys.path.insert(0, "${SHARE}/${APP_NAME}"); from persistent_claude_code.__main__ import main; raise SystemExit(main())' "\$@"
EOF
chmod +x "${BIN}/${APP_NAME}"

install -Dm644 "${REPO_ROOT}/data/${APP_ID}.desktop" "${SHARE}/applications/${APP_ID}.desktop"
install -Dm644 "${REPO_ROOT}/data/${APP_ID}.svg" "${SHARE}/icons/hicolor/scalable/apps/${APP_ID}.svg"

if command -v update-desktop-database >/dev/null 2>&1; then
  update-desktop-database "${SHARE}/applications" || true
fi
if command -v gtk-update-icon-cache >/dev/null 2>&1; then
  gtk-update-icon-cache -q -t -f "${SHARE}/icons/hicolor" || true
fi

echo "Installed ${APP_NAME} to ${PREFIX}"
echo "Launch from the app grid or run: ${APP_NAME}"
```

- [ ] **Step 2: Create `uninstall.sh`**

```bash
#!/usr/bin/env bash
set -euo pipefail

APP_ID=io.github.seulsale.PersistentClaudeCode
APP_NAME=persistent-claude-code
PREFIX="${HOME}/.local"
SHARE="${PREFIX}/share"
BIN="${PREFIX}/bin"

rm -f "${BIN}/${APP_NAME}"
rm -rf "${SHARE}/${APP_NAME}"
rm -f "${SHARE}/applications/${APP_ID}.desktop"
rm -f "${SHARE}/icons/hicolor/scalable/apps/${APP_ID}.svg"

if command -v update-desktop-database >/dev/null 2>&1; then
  update-desktop-database "${SHARE}/applications" || true
fi
if command -v gtk-update-icon-cache >/dev/null 2>&1; then
  gtk-update-icon-cache -q -t -f "${SHARE}/icons/hicolor" || true
fi

echo "Uninstalled ${APP_NAME}"
```

- [ ] **Step 3: Make executable and test end-to-end**

Run:

```bash
chmod +x install.sh uninstall.sh
./install.sh
persistent-claude-code &
# verify the window opens, then close it
./uninstall.sh
```

Expected: installer copies files, app launches from `~/.local/bin/persistent-claude-code`, uninstaller cleans everything up.

- [ ] **Step 4: Commit**

```bash
git add install.sh uninstall.sh
git commit -m "chore: add install.sh and uninstall.sh"
```

---

## Task 17: AUR PKGBUILD

**Files:**
- Create: `packaging/aur/PKGBUILD`
- Create: `packaging/aur/.SRCINFO`

- [ ] **Step 1: Create `packaging/aur/PKGBUILD`**

```bash
# Maintainer: seulsale <sergio.saucedo10@gmail.com>
pkgname=persistent-claude-code-git
_pkgname=persistent-claude-code
pkgver=0.1.0.r0.g0000000
pkgrel=1
pkgdesc="GTK desktop app for browsing and resuming Claude Code sessions"
arch=('any')
url="https://github.com/seulsale/persistent-claude-code"
license=('MIT')
depends=('python>=3.14' 'python-gobject' 'gtk4' 'libadwaita' 'vte4' 'webkitgtk-6.0')
makedepends=('git')
provides=("${_pkgname}")
conflicts=("${_pkgname}")
source=("git+${url}.git")
sha256sums=('SKIP')

pkgver() {
  cd "${srcdir}/${_pkgname}"
  printf "0.1.0.r%s.g%s" "$(git rev-list --count HEAD)" "$(git rev-parse --short HEAD)"
}

package() {
  cd "${srcdir}/${_pkgname}"

  install -d "${pkgdir}/usr/share/${_pkgname}"
  cp -r src/persistent_claude_code "${pkgdir}/usr/share/${_pkgname}/"

  install -d "${pkgdir}/usr/bin"
  cat > "${pkgdir}/usr/bin/${_pkgname}" <<EOF
#!/usr/bin/env bash
exec python3 -c 'import sys; sys.path.insert(0, "/usr/share/${_pkgname}"); from persistent_claude_code.__main__ import main; raise SystemExit(main())' "\$@"
EOF
  chmod +x "${pkgdir}/usr/bin/${_pkgname}"

  install -Dm644 "data/io.github.seulsale.PersistentClaudeCode.desktop" \
    "${pkgdir}/usr/share/applications/io.github.seulsale.PersistentClaudeCode.desktop"
  install -Dm644 "data/io.github.seulsale.PersistentClaudeCode.svg" \
    "${pkgdir}/usr/share/icons/hicolor/scalable/apps/io.github.seulsale.PersistentClaudeCode.svg"
  install -Dm644 LICENSE "${pkgdir}/usr/share/licenses/${_pkgname}/LICENSE"
}
```

- [ ] **Step 2: Generate `.SRCINFO`**

Run (from `packaging/aur/`): `makepkg --printsrcinfo > .SRCINFO`

Expected: `.SRCINFO` file is written. Inspect it; it should match the PKGBUILD fields.

- [ ] **Step 3: Local build test**

Run (from `packaging/aur/`): `makepkg -s --noconfirm`

Expected: produces a `.pkg.tar.zst` file. Install with `sudo pacman -U ./persistent-claude-code-git-*.pkg.tar.zst`, verify `persistent-claude-code` launches from the app grid, then remove with `sudo pacman -R persistent-claude-code-git`.

- [ ] **Step 4: Commit**

```bash
git add packaging/
git commit -m "chore(packaging): add AUR PKGBUILD and .SRCINFO"
```

---

## Task 18: GitHub Actions release workflow

**Files:**
- Create: `.github/workflows/release.yml`

- [ ] **Step 1: Create the workflow**

```yaml
name: Release

on:
  push:
    tags:
      - "v*.*.*"

jobs:
  build-arch-package:
    runs-on: ubuntu-latest
    container: archlinux:latest
    steps:
      - name: Install deps
        run: |
          pacman -Syu --noconfirm base-devel git python python-gobject gtk4 libadwaita vte4 webkitgtk-6.0
          useradd -m builder
          echo "builder ALL=(ALL) NOPASSWD: ALL" >> /etc/sudoers

      - uses: actions/checkout@v4

      - name: Build package
        run: |
          chown -R builder:builder .
          su builder -c "cd packaging/aur && makepkg -s --noconfirm"

      - name: Upload release asset
        uses: softprops/action-gh-release@v2
        with:
          files: packaging/aur/*.pkg.tar.zst
```

- [ ] **Step 2: Commit**

```bash
git add .github/workflows/release.yml
git commit -m "ci: build and attach pacman package on release tag"
```

---

## Task 19: README

**Files:**
- Create: `README.md`

- [ ] **Step 1: Create `README.md`**

```markdown
# Persistent Claude Code

A local GTK4 / GNOME desktop app for browsing and resuming Claude Code sessions without opening a terminal, navigating to the project, and running `claude --resume <id>`.

![screenshot placeholder](docs/screenshots/main.png)

## Features (v0.1.0)

- Sidebar browser of all sessions under `~/.claude/projects/`, grouped by project, sorted by recency.
- Fuzzy filter across project paths and session titles (Ctrl+K).
- One-click resume: each session opens in a tab running `claude --resume <id>` inside an embedded VTE terminal.
- `+ New session` row per project for starting a fresh `claude` without leaving the app.
- Embedded WebKit browser pane per tab (Ctrl+Shift+B), with back/forward/reload and a URL bar.
- Live status dots on the sidebar: green (working), yellow (waiting), grey (idle) — for sessions currently running in the app.
- "Session ended" placeholder with Resume / Close buttons when `claude` exits.
- Libadwaita theming; follows system light/dark.
- Keyboard shortcuts for every common action.

## Install

### Recommended — AUR

```bash
yay -S persistent-claude-code-git
```

### From GitHub Release (pacman)

```bash
sudo pacman -U ./persistent-claude-code-*.pkg.tar.zst
```

### From source

```bash
./install.sh
./uninstall.sh   # to undo
```

## Requirements

Arch packages:

- `python` (3.14+)
- `python-gobject`
- `gtk4`
- `libadwaita`
- `vte4`
- `webkitgtk-6.0`

And the [`claude`](https://docs.anthropic.com/claude/docs/claude-code) CLI installed and on `$PATH`.

## Config

`~/.config/persistent-claude-code/config.json`:

| Key | Default | Meaning |
| --- | --- | --- |
| `terminal_font` | `"Monospace 11"` | Pango font for the VTE terminal. |
| `terminal_scrollback` | `10000` | Terminal scrollback line count. |
| `claude_binary` | `null` | Absolute path to `claude`; `null` = resolve via `$PATH`. |
| `browser_home` | `"about:blank"` | Initial URL for newly-toggled browser panes. |
| `window_size` | `[1400, 900]` | Window size; persisted automatically. |

## Keybindings

| Shortcut | Action |
| --- | --- |
| `Ctrl+K` | Focus sidebar search |
| `Ctrl+T` | Focus "+ New session" of the first project |
| `Ctrl+W` | Close current tab |
| `Ctrl+Tab` / `Ctrl+Shift+Tab` | Cycle tabs |
| `Ctrl+Shift+B` | Toggle browser pane |
| `Ctrl+?` | About dialog |

## Roadmap (post v1)

- Full-text search across all messages.
- In-app settings dialog.
- Per-session notes / tags / favourites.
- System tray integration.
- Multi-distro packaging (Flatpak, Debian, etc.).
- Multiple windows.

## License

MIT.
```

- [ ] **Step 2: Commit**

```bash
git add README.md
git commit -m "docs: README with features, install, config, and keybindings"
```

---

## Task 20: End-to-end verification

**Files:** (none — verification only)

- [ ] **Step 1: Full test run**

Run: `python3 -m pytest -v`
Expected: all tests pass across `tests/test_config.py`, `tests/test_sessions.py`, `tests/test_status.py`.

- [ ] **Step 2: Lint**

Run: `python3 -m ruff check`
Expected: `All checks passed!`.

- [ ] **Step 3: Manual golden path**

Run: `make run`

Verify in order:
1. App opens to the empty-state status page with a populated sidebar.
2. Typing in the search narrows the tree; Enter launches the first visible session.
3. Clicking a session opens a tab with claude resumed in the right cwd.
4. Clicking the same session focuses the existing tab (no duplicate).
5. Clicking `+ New session` opens a fresh claude in the project cwd; its jsonl appears in the sidebar within a second.
6. A live status dot appears and transitions green → yellow as you interact.
7. `Ctrl+Shift+B` toggles a WebKit pane; navigating to a URL works.
8. `Ctrl+W` closes a tab; the ended card appears if claude was still running.
9. `Ctrl+?` shows version 0.1.0.
10. Closing the window and reopening restores the same window size; no tabs restore.

- [ ] **Step 4: Fresh-install verification**

Run: `./install.sh && persistent-claude-code &`
Then close the app, `./uninstall.sh`, confirm `persistent-claude-code` is gone.

- [ ] **Step 5: Tag the release**

```bash
git tag -a v0.1.0 -m "v0.1.0"
```

(Do not push without confirmation.)

- [ ] **Step 6: Final commit if anything changed during verification**

If steps 1-4 revealed issues, fix them in focused commits, then repeat.
