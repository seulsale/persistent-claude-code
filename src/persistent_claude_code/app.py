from __future__ import annotations

from pathlib import Path

from gi.repository import Adw, Gio, GLib, Gtk

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

        from persistent_claude_code.claude_binary import resolve_claude_binary
        from persistent_claude_code.sidebar import Sidebar
        from persistent_claude_code.tab import SessionTab

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
        self._status_monitors: dict[str, object] = {}
        self.connect("close-request", self._on_close_request)
        self._install_shortcuts()

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
        from persistent_claude_code.status import SessionStatusMonitor

        tab = self._SessionTab(
            config=self._app.config,
            session_id=session_id,
            cwd=cwd,
            argv=argv,
            on_close_requested=self._request_close_tab,
            extra_env={"BROWSER": "persistent-claude-code --open-url"},
        )
        page = self._tabs.append(tab)
        page.set_title(title[:30])
        page.set_tooltip(tooltip)
        if session_id is not None:
            self._session_pages[session_id] = page

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
        for project in self.sidebar._model.projects:  # noqa: SLF001
            for s in project.sessions:
                if s.id == session_id:
                    return s.jsonl_path
        return None

    def _request_close_tab(self, tab) -> None:
        page = self._tabs.get_page(tab)
        self._tabs.close_page(page)

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

    def _install_shortcuts(self) -> None:
        controller = Gtk.ShortcutController()
        controller.set_scope(Gtk.ShortcutScope.GLOBAL)
        # Capture phase so VTE doesn't swallow the keystrokes before us.
        controller.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)

        def make_action(callback):
            def _action(*_args):
                callback()
                return True
            return Gtk.CallbackAction.new(_action)

        def shortcut(accel: str, cb):
            trig = Gtk.ShortcutTrigger.parse_string(accel)
            controller.add_shortcut(Gtk.Shortcut.new(trig, make_action(cb)))

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

    def open_url_in_current_tab(self, url: str) -> None:
        tab = self._current_tab()
        if tab is None or not hasattr(tab, "show_browser_with_url"):
            self.toast(f"Open a session tab first to use the browser for: {url}")
            return
        tab.show_browser_with_url(url)

    def _toggle_current_browser(self) -> None:
        tab = self._current_tab()
        if tab is not None and hasattr(tab, "toggle_browser"):
            tab.toggle_browser()

    def _focus_new_session_of_current_project(self) -> None:
        tree = self.sidebar._tree  # noqa: SLF001
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
            flags=Gio.ApplicationFlags.HANDLES_COMMAND_LINE,
        )
        self.config: Config = load_config()
        self._window: MainWindow | None = None

        self.add_main_option(
            "open-url",
            0,
            GLib.OptionFlags.NONE,
            GLib.OptionArg.STRING,
            "Open the given URL in the current tab's browser pane",
            "URL",
        )

    def do_activate(self) -> None:
        if self._window is None:
            self._window = MainWindow(self)
        self._window.present()

    def do_command_line(self, command_line: Gio.ApplicationCommandLine) -> int:
        options = command_line.get_options_dict()
        url_variant = options.lookup_value("open-url", None)

        self.activate()  # ensures the window exists

        if url_variant is not None:
            url = url_variant.get_string()
            if self._window is not None:
                self._window.open_url_in_current_tab(url)
        return 0
