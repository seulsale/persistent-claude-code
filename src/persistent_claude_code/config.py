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
