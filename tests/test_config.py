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
