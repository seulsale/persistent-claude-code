from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

from gi.repository import Gio, GLib, Gtk

from persistent_claude_code.sessions import (
    CLAUDE_PROJECTS_DIR,
    Model,
    Project,
    Session,
    filter_sessions,
    scan_projects,
)

_STATE_ICON = {
    "working": ("● Working", "#33d17a"),
    "waiting": ("● Waiting for input", "#f5c211"),
    "idle":    ("● Idle", "#9a9996"),
}

OnOpenSession = Callable[[Session], None]
OnNewSession = Callable[[Project], None]


def _relative_time(ts: float) -> str:
    now = datetime.now(tz=UTC).timestamp()
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
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2, margin_top=8, margin_bottom=8, margin_start=10, margin_end=10)
        title = Gtk.Label(label=session.title, xalign=0, ellipsize=3, max_width_chars=40)
        title.set_single_line_mode(True)
        title.set_lines(1)
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

        self._tree = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        self._tree.set_margin_top(2)
        self._tree.set_margin_bottom(6)
        scrolled = Gtk.ScrolledWindow(hscrollbar_policy=Gtk.PolicyType.NEVER, vexpand=True)
        scrolled.set_child(self._tree)
        self.append(scrolled)

        self._model = Model()
        self._rows: dict[str, _SessionRow] = {}
        self._expanded_projects: set[str] = set()

        self._root_monitor: Gio.FileMonitor | None = None
        self._subdir_monitors: dict[str, Gio.FileMonitor] = {}

    def refresh(self) -> None:
        self._model = scan_projects(CLAUDE_PROJECTS_DIR)
        self._rebuild()
        self._refresh_subdir_monitors()

    def start_watching(self) -> None:
        if self._root_monitor is not None:
            return
        CLAUDE_PROJECTS_DIR.mkdir(parents=True, exist_ok=True)
        gio_dir = Gio.File.new_for_path(str(CLAUDE_PROJECTS_DIR))
        self._root_monitor = gio_dir.monitor_directory(Gio.FileMonitorFlags.WATCH_MOVES, None)
        self._root_monitor.connect("changed", self._on_fs_changed)
        self._refresh_subdir_monitors()

    def _refresh_subdir_monitors(self) -> None:
        # Gio.FileMonitor on a directory only reports events for its direct
        # children. Since Claude writes new sessions into per-project subdirs,
        # we also watch each subdir so new JSONL files trigger a refresh.
        if not CLAUDE_PROJECTS_DIR.is_dir():
            return
        current: set[str] = set()
        for sub in CLAUDE_PROJECTS_DIR.iterdir():
            if not sub.is_dir():
                continue
            current.add(str(sub))
            if str(sub) in self._subdir_monitors:
                continue
            gio_sub = Gio.File.new_for_path(str(sub))
            mon = gio_sub.monitor_directory(Gio.FileMonitorFlags.WATCH_MOVES, None)
            mon.connect("changed", self._on_fs_changed)
            self._subdir_monitors[str(sub)] = mon
        # Drop monitors for subdirs that no longer exist.
        for gone in set(self._subdir_monitors) - current:
            mon = self._subdir_monitors.pop(gone)
            mon.cancel()

    def _on_fs_changed(self, *_a: object) -> None:
        # Debounce: schedule a refresh on next idle; multiple events coalesce.
        GLib.idle_add(self._debounced_refresh)

    def _debounced_refresh(self) -> bool:
        self.refresh()
        return False

    def expanded_projects(self) -> list[str]:
        return sorted(self._expanded_projects)

    def set_expanded_projects(self, paths: list[str]) -> None:
        self._expanded_projects = set(paths)
        self._rebuild()

    def get_row_for_session(self, session_id: str) -> _SessionRow | None:
        return self._rows.get(session_id)

    def set_session_state(self, session_id: str, state: str | None) -> None:
        row = self._rows.get(session_id)
        if row is None:
            return
        if state is None:
            row.status_dot.set_visible(False)
            row.set_tooltip_text(None)
            return

        label, color = _STATE_ICON[state]
        markup = f'<span foreground="{color}">●</span>'
        # Replace the image with a Gtk.Label for colored text.
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

    def _rebuild(self) -> None:
        child = self._tree.get_first_child()
        while child is not None:
            self._tree.remove(child)
            child = self._tree.get_first_child()
        self._rows = {}

        query = self.search.get_text()
        visible = filter_sessions(query, self._model)

        for project in visible.projects:
            starts_expanded = project.path in self._expanded_projects
            expander = Gtk.Expander(expanded=starts_expanded)
            expander.set_label_widget(_project_label_widget(project))
            expander.set_margin_start(6)
            expander.set_margin_end(6)
            expander.set_margin_top(2)
            expander.set_margin_bottom(2)
            expander.add_css_class("pcc-folder")
            if not project.exists:
                expander.set_tooltip_text(f"{project.path} (directory does not exist)")
                expander.add_css_class("dim-label")
            else:
                expander.set_tooltip_text(project.path)

            expander.connect(
                "notify::expanded",
                self._on_expander_toggled,
                project.path,
            )

            listbox = Gtk.ListBox()
            listbox.set_selection_mode(Gtk.SelectionMode.NONE)
            listbox.set_show_separators(True)
            listbox.add_css_class("navigation-sidebar")
            listbox.add_css_class("boxed-list")
            listbox.set_margin_top(4)
            listbox.set_margin_start(4)
            listbox.set_margin_end(4)
            listbox.set_margin_bottom(4)
            listbox.connect("row-activated", self._on_row_activated)

            new_row = _NewSessionRow(project)
            listbox.append(new_row)

            for s in project.sessions:
                row = _SessionRow(s)
                self._rows[s.id] = row
                listbox.append(row)

            expander.set_child(listbox)
            self._tree.append(expander)

    def _on_expander_toggled(self, expander: Gtk.Expander, _pspec: object, project_path: str) -> None:
        if expander.get_expanded():
            self._expanded_projects.add(project_path)
        else:
            self._expanded_projects.discard(project_path)

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


def _project_label_widget(project: Project) -> Gtk.Widget:
    base = Path(project.path).name or project.path
    box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
    box.set_margin_top(6)
    box.set_margin_bottom(6)
    box.set_margin_start(4)
    box.set_margin_end(6)
    box.set_hexpand(True)

    icon_name = "folder-symbolic" if project.exists else "folder-visiting-symbolic"
    icon = Gtk.Image.new_from_icon_name(icon_name)
    icon.set_pixel_size(16)
    box.append(icon)

    text_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=1)
    text_box.set_hexpand(True)
    name = Gtk.Label(label=base, xalign=0, ellipsize=3, max_width_chars=32)
    name.set_single_line_mode(True)
    name.add_css_class("heading")
    text_box.append(name)

    count = len(project.sessions)
    caption_text = f"{count} session{'s' if count != 1 else ''}"
    caption = Gtk.Label(label=caption_text, xalign=0)
    caption.add_css_class("dim-label")
    caption.add_css_class("caption")
    text_box.append(caption)
    box.append(text_box)

    return box
