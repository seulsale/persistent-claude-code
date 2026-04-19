from __future__ import annotations

from pathlib import Path

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
        return True

    def _on_open_session(self, session) -> None:
        existing = self._session_pages.get(session.id)
        if existing is not None:
            self._tabs.set_selected_page(existing)
            return

        argv = self._claude_argv(session.id)
        if argv is None:
            self.toast("claude not found — install Claude Code CLI")
            return

        if not Path(session.project_path).is_dir():
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
        if not Path(project.path).is_dir():
            self.toast(f"Directory {project.path} doesn't exist; session may fail to launch.")
        self._open_tab(
            title=f"New · {Path(project.path).name}",
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
