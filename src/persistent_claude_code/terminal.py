from __future__ import annotations

import shutil
from collections.abc import Callable
from pathlib import Path

from gi.repository import GLib, Gtk, Vte

OnExited = Callable[[int], None]

_NORD_BG = "#2e3440"
_NORD_FG = "#d8dee9"
_NORD_PALETTE = [
    "#3b4252",  # 0  black
    "#bf616a",  # 1  red
    "#a3be8c",  # 2  green
    "#ebcb8b",  # 3  yellow
    "#81a1c1",  # 4  blue
    "#b48ead",  # 5  magenta
    "#88c0d0",  # 6  cyan
    "#e5e9f0",  # 7  white
    "#4c566a",  # 8  bright black
    "#bf616a",  # 9  bright red
    "#a3be8c",  # 10 bright green
    "#ebcb8b",  # 11 bright yellow
    "#81a1c1",  # 12 bright blue
    "#b48ead",  # 13 bright magenta
    "#eceff4",  # 14 bright white
    "#8fbcbb",  # 15 extra cyan
]


def _apply_nord_theme(terminal: Vte.Terminal) -> None:
    from gi.repository import Gdk
    def parse(hex_color: str) -> Gdk.RGBA:
        rgba = Gdk.RGBA()
        rgba.parse(hex_color)
        return rgba

    palette = [parse(c) for c in _NORD_PALETTE]
    terminal.set_colors(parse(_NORD_FG), parse(_NORD_BG), palette)


def resolve_claude_binary(override: str | None) -> str | None:
    if override:
        return override if Path(override).is_file() else None
    return shutil.which("claude")


class TerminalPane(Gtk.Box):
    __gtype_name__ = "PCCTerminalPane"

    def __init__(self, font: str, scrollback: int, on_exited: OnExited | None = None) -> None:
        super().__init__(orientation=Gtk.Orientation.VERTICAL, hexpand=True, vexpand=True)
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
        self.terminal.set_margin_top(8)
        self.terminal.set_margin_bottom(8)
        self.terminal.set_margin_start(8)
        self.terminal.set_margin_end(8)
        self.terminal.connect("child-exited", self._on_child_exited)
        _apply_nord_theme(self.terminal)
        self.terminal.set_hexpand(True)
        self.terminal.set_vexpand(True)

        self._stack.add_named(self.terminal, "terminal")

        self._ended_box = self._build_ended_box()
        self._stack.add_named(self._ended_box, "ended")

        self._stack.set_hexpand(True)
        self._stack.set_vexpand(True)
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
            None,
            GLib.SpawnFlags.DEFAULT,
            None, None,
            -1,
            None,
            None,
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
        return page.root

    def _on_resume_clicked(self, _btn: Gtk.Button) -> None:
        if self._on_resume_callback is not None:
            self._on_resume_callback()


def _font_description(font_string: str):
    try:
        from gi.repository import Pango
        return Pango.FontDescription.from_string(font_string)
    except GLib.Error:
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
