from __future__ import annotations

from gi.repository import Adw, Gio

from persistent_claude_code.config import Config
from persistent_claude_code.config import load as load_config
from persistent_claude_code.config import save as save_config

APP_ID = "io.github.seulsale.PersistentClaudeCode"
APP_NAME = "Persistent Claude Code"


class MainWindow(Adw.ApplicationWindow):
    def __init__(self, app: App) -> None:
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
