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
        on_close_requested: Callable[[SessionTab], None],
        extra_env: dict[str, str] | None = None,
        start_dormant: bool = False,
        dormant_title: str = "",
        dormant_detail: str = "",
        dormant_resume_label: str = "Resume",
    ) -> None:
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self.session_id = session_id
        self.cwd = cwd
        self._argv = argv
        self._config = config
        self._on_close_requested = on_close_requested
        self._extra_env = extra_env

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
        if start_dormant:
            self.terminal.show_dormant(dormant_title, dormant_detail, dormant_resume_label)
        else:
            self.terminal.spawn(argv, cwd, extra_env=extra_env)
        self.terminal._close_button.connect("clicked", lambda *_: self._on_close_requested(self))  # noqa: SLF001

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

    def show_browser_with_url(self, url: str) -> None:
        if not self._browser_toggle.get_active():
            self._browser_toggle.set_active(True)
        if self._browser is not None:
            self._browser.load_url(url)

    def _resume(self) -> None:
        self.terminal.spawn(self._argv, self.cwd, extra_env=self._extra_env)
