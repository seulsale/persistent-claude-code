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

        main_toolbar = Adw.ToolbarView()
        main_toolbar.add_top_bar(Adw.HeaderBar())
        main_toolbar.set_content(placeholder)

        from persistent_claude_code.sidebar import Sidebar

        self.sidebar = Sidebar(on_open=self._on_open_session, on_new=self._on_new_session)
        self.sidebar.refresh()
        self.sidebar.start_watching()

        sidebar_toolbar = Adw.ToolbarView()
        sidebar_toolbar.add_top_bar(Adw.HeaderBar())
        sidebar_toolbar.set_content(self.sidebar)

        split = Adw.OverlaySplitView()
        split.set_sidebar(sidebar_toolbar)
        split.set_content(main_toolbar)
        split.set_show_sidebar(True)
        split.set_min_sidebar_width(260)
        split.set_sidebar_width_fraction(0.25)
        self.set_content(split)

        self.connect("close-request", self._on_close_request)

    def _on_open_session(self, session) -> None:
        print(f"(todo) open session {session.id} in {session.project_path}")

    def _on_new_session(self, project) -> None:
        print(f"(todo) new session in {project.path}")

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
