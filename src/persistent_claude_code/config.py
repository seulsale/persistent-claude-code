from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field, fields
from pathlib import Path


@dataclass(frozen=True)
class SavedTab:
    kind: str  # "resume" or "new"
    session_id: str | None
    title: str
    cwd: str


@dataclass(frozen=True)
class Config:
    terminal_font: str = "JetBrains Mono 11"
    terminal_scrollback: int = 10000
    claude_binary: str | None = None
    browser_home: str = "about:blank"
    window_size: tuple[int, int] = field(default=(1400, 900))
    open_tabs: tuple[SavedTab, ...] = ()
    expanded_projects: tuple[str, ...] = ()


def default_path() -> Path:
    base = os.environ.get("XDG_CONFIG_HOME") or str(Path.home() / ".config")
    return Path(base) / "persistent-claude-code" / "config.json"


def _parse_saved_tab(raw: object) -> SavedTab | None:
    if not isinstance(raw, dict):
        return None
    kind = raw.get("kind")
    title = raw.get("title")
    cwd = raw.get("cwd")
    session_id = raw.get("session_id")
    if kind not in ("resume", "new"):
        return None
    if not isinstance(title, str) or not isinstance(cwd, str):
        return None
    if session_id is not None and not isinstance(session_id, str):
        return None
    if kind == "resume" and not session_id:
        return None
    return SavedTab(kind=kind, session_id=session_id, title=title, cwd=cwd)


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
        elif key == "open_tabs" and isinstance(value, list):
            parsed = tuple(t for t in (_parse_saved_tab(item) for item in value) if t is not None)
            kwargs[key] = parsed
        elif key == "expanded_projects" and isinstance(value, list):
            kwargs[key] = tuple(v for v in value if isinstance(v, str))
        else:
            kwargs[key] = value
    return Config(**kwargs)  # type: ignore[arg-type]


def save(cfg: Config, path: Path | None = None) -> None:
    path = path or default_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    data = asdict(cfg)
    data["window_size"] = list(cfg.window_size)
    data["open_tabs"] = [asdict(t) for t in cfg.open_tabs]
    data["expanded_projects"] = list(cfg.expanded_projects)
    path.write_text(json.dumps(data, indent=2))
