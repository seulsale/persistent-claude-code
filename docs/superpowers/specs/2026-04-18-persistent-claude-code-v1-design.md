# Persistent Claude Code — v1 design

- **Version:** 0.1.0 (semver)
- **Date:** 2026-04-18
- **Status:** approved

## 1. Overview

A local GTK4 / GNOME desktop app for browsing and resuming Claude Code sessions without opening a terminal, navigating to the project, and running `claude --resume`.

The app shows all past sessions in a sidebar, grouped by project. One click launches a session inside an embedded terminal (VTE). Each session tab can toggle a side-by-side embedded browser (WebKitGTK) — useful for Playwright MCP workflows and visual brainstorming companions. Live status dots in the sidebar show which sessions launched from the app are working, waiting, or idle.

## 2. Decisions summary

| Area | Decision |
|---|---|
| Scope | Embedded terminal + embedded browser per session |
| Stack | Python 3.14+, PyGObject, GTK4, Libadwaita, VTE4, WebKitGTK 6 |
| Layout | Persistent left sidebar + main tab area |
| Session title | Last user prompt (truncated) + relative time + git branch |
| Click behavior | Single click launches immediately in a new tab |
| Live status | Only for sessions launched from this app; 4 states |
| New sessions | `+ New session` entry at the top of each project |
| Tab on claude exit | "Session ended" placeholder with Resume / Close |
| Browser | Toggleable right-side pane per session tab (split view) |
| Search | Client-side fuzzy filter over project + session title; full-text is v2 |
| Persistence | Always start empty; only window size persists |
| Installation | AUR package (primary) + pre-built `.pkg.tar.zst` release + `install.sh` fallback |
| Flatpak | Explicitly out of scope |

## 3. Architecture

### Stack

- **Runtime:** Python 3.14+.
- **GUI:** PyGObject bindings over GTK4 and Libadwaita.
- **Terminal widget:** VTE4 (`Vte.Terminal`).
- **Browser widget:** WebKitGTK 6 (`WebKit.WebView`).
- **Arch packages required:** `python`, `python-gobject`, `gtk4`, `libadwaita`, `vte4`, `webkitgtk-6.0`.

### Process model

Single GTK app, one process. Each session tab spawns a child process inside its `Vte.Terminal` (typically `claude --resume <id>`). The app itself only runs GIO file monitors and GLib timers; no background threads in v1.

### Data

No database. On startup, the app scans `~/.claude/projects/` and builds an in-memory model of projects and sessions. The model is updated incrementally via `Gio.FileMonitor`. A single JSON config file under `$XDG_CONFIG_HOME/persistent-claude-code/config.json` stores user prefs.

### Module layout

```
src/persistent_claude_code/
  __init__.py        — exports __version__
  __main__.py        — python -m entry point
  main.py            — Adw.Application bootstrap
  app.py             — main window, top-level OverlaySplitView
  sessions.py        — scan, parse, model; filter_sessions()
  status.py          — per-session state machine (Working/Waiting/Idle)
  sidebar.py         — projects tree widget + search entry
  tab.py             — one tab = terminal pane + optional browser pane
  terminal.py        — Vte.Terminal wrapper + "session ended" placeholder
  browser.py         — WebKit.WebView wrapper + URL bar
  config.py          — load/save config.json
```

Each module has a single responsibility. `sessions.py` and `status.py` are pure-model (no GTK imports) and testable in isolation.

## 4. UI layout

### Window

`Adw.ApplicationWindow` wraps an `Adw.OverlaySplitView` (sidebar + main).

### Sidebar

- **Header:** app title + a search entry (`Gtk.SearchEntry`). `Ctrl+K` focuses the entry.
- **Body:** scrollable list of projects. Each project is an expander:
  - **Header row:** project name (basename of the decoded cwd). Tooltip shows full path. Greyed out if the cwd no longer exists on disk.
  - **First child row:** `+ New session`.
  - **Session rows:** one per `.jsonl`, newest first. Each shows the session title (last user prompt, ellipsized), relative time ("2h ago"), and git branch. A small colored status dot appears on the right when the session is live.
- Projects are ordered by most-recent session activity (mtime of newest jsonl).

### Main pane

`Adw.TabView` with an `Adw.TabBar` on top. Each tab is a session tab whose content is itself an `Adw.OverlaySplitView`:

- **Primary child:** `Vte.Terminal` running the spawned claude command.
- **Secondary child (hidden by default):** `WebKit.WebView` with a thin URL bar (`Gtk.Entry` + back / forward / reload buttons).
- A toggle button flips the browser pane on/off. Keyboard: `Ctrl+Shift+B`.

### Empty state

When no tabs are open, the main pane shows an `Adw.StatusPage` with the text *"Pick a session from the sidebar, or start a new one."*

### Theming

Libadwaita follows system light/dark mode. VTE's color palette and WebKit's default background are selected to match the current Adwaita theme variant.

### Keyboard shortcuts

| Shortcut | Action |
|---|---|
| `Ctrl+K` | Focus sidebar search |
| `Ctrl+T` | Focus `+ New session` of the currently expanded project |
| `Ctrl+W` | Close current tab |
| `Ctrl+Tab` / `Ctrl+Shift+Tab` | Cycle tabs |
| `Ctrl+Shift+B` | Toggle browser pane for current tab |
| `Ctrl+?` | About dialog |

## 5. Session discovery & metadata

### Discovery

On startup, scan `~/.claude/projects/`. Each subdirectory whose name starts with `-` is a project — the directory name is the project's cwd with `/` replaced by `-`. Decode back to the real path. If that path no longer exists on disk, mark the project as *orphaned*: it stays listed but is visually greyed out; its sessions are still launchable.

### Per-session metadata

From each `.jsonl`:

- **`session_id`** — filename without `.jsonl`.
- **`title`** — text of the most recent `last-prompt` entry; if none, the text of the first `user`-type message; if none, the literal `"Untitled session"`. Truncated to ~80 chars for display.
- **`branch`** — `gitBranch` field from the most recent entry that carries it.
- **`last_activity`** — file mtime.
- **`message_count`** — count of non-sidechain `user` and `assistant` lines. Computed lazily; exposed by the model but not shown in v1 UI.

### Parsing strategy

Tail-read only the last ~200 KB of each `.jsonl` during scan. Extract the last `last-prompt` text and the most recent `gitBranch`. Full-file parsing is reserved for the v2 full-text index.

### Live discovery

A `Gio.FileMonitor` on `~/.claude/projects/` catches new project directories and new session files. New sessions appear in the sidebar without requiring a restart.

### Orphan handling

When launching a session whose cwd no longer exists, spawn the claude command anyway (claude itself will surface the error). Show an `Adw.Toast` in the main window: *"Directory `<path>` doesn't exist; session may fail to resume."*

## 6. Launch & tab lifecycle

### Clicking a session row

1. If a tab is already open for that `session_id` → focus it and return.
2. Otherwise create an `Adw.TabPage`. Tab label is the session title truncated to ~30 chars; tooltip is the full title + session id.
3. Inside the tab's `Vte.Terminal`, spawn `claude --resume <session_id>` with `cwd` set to the decoded project path. Inherit the app's environment plus `TERM=xterm-256color`. No wrapping shell.
4. If the `claude` binary is not on `$PATH` (and `config.claude_binary` is null), show a toast *"claude not found — install Claude Code CLI"* and close the tab.

### Clicking `+ New session` in a project

Same as above but spawn `claude` with no `--resume` argument. The new session's `.jsonl` will appear via the file monitor as soon as claude writes its first event, and a new row will be added live to the project.

### Tab lifecycle on child exit

The VTE `child-exited` signal fires when the child process terminates. The terminal widget is replaced in-place by a centered placeholder card showing:

- The session id.
- The exit code (only when non-zero).
- Two buttons: **Resume** (respawns `claude --resume <id>` in the same cwd, restoring the terminal widget) and **Close** (destroys the tab).

The browser pane, if open, is unaffected.

### Closing a running tab

Closing a tab while its child is still alive sends `SIGTERM` to the VTE child. No confirmation dialog.

### Browser pane default

When a browser pane is toggled on for the first time in a tab, the initial URL is `config.browser_home` (default `about:blank`). Subsequent toggles preserve the current URL and history for that tab. The URL bar accepts any input; navigation happens on `Enter`. No auto-open or link detection from terminal output.

## 7. Live status tracking

Live status is tracked **only for sessions currently running in an app tab**. We know which `.jsonl` maps to which tab because the app spawned the child.

### State machine

| State | Condition |
|---|---|
| 🟢 Working | `.jsonl` modified within the last 2 seconds |
| 🟡 Waiting | Last modification between 2 s and 5 min ago, *and* the last complete JSONL line has `"type":"assistant"` |
| ⚪ Idle | No modification in 5 min or more, *or* the last complete line is neither user nor assistant (likely mid-stream) |
| no dot | No tab is currently running this session |

### Implementation

- Per-tab `Gio.FileMonitor` on the session's `.jsonl`. The `CHANGED` signal updates an in-memory "last write" timestamp and triggers a state recompute.
- A 1 Hz GLib timeout recomputes state for all live sessions. State changes are pushed to the sidebar; no dot redraw happens while state is unchanged.
- Determining "last complete line": tail the file, seek to the last `\n`, then try `json.loads` on the slice between the previous `\n` and EOF. Parse failure ⇒ treat as streaming (Working).
- When the VTE `child-exited` signal fires, the session state is set to "no dot" immediately, regardless of file timestamps.

### UI

An 8 px colored circle at the right edge of the session row in the sidebar. Tooltip shows the state label plus "last active: 3s ago".

## 8. Search

Client-side fuzzy substring filter over the in-memory model. No database, no index.

- Search entry at the top of the sidebar; `Ctrl+K` focuses.
- Matches are case-insensitive substring (simple; fuzzy-ranking is not worth the dependency in v1) against: project name, decoded cwd, session title.
- Computed on every keystroke; model size is small.
- While the search box is non-empty:
  - Non-matching sessions are hidden.
  - A project is hidden only if **all** its sessions are hidden **and** its own name doesn't match.
  - Matching projects auto-expand.
  - Pressing `Enter` launches the first visible session (same semantics as section 6).
- `Esc` clears the search and restores the prior expansion state.

### v2 hook

The filter is a pure function in `sessions.py`:

```python
def filter_sessions(query: str, model: Model) -> FilteredView: ...
```

When full-text search arrives in v2, the signature stays the same; only the implementation and the offline index change.

## 9. Config & state persistence

### Config file

`$XDG_CONFIG_HOME/persistent-claude-code/config.json` (default `~/.config/...`). Created with defaults on first launch. User-editable; there is no in-app settings dialog in v1.

```json
{
  "terminal_font": "Monospace 11",
  "terminal_scrollback": 10000,
  "claude_binary": null,
  "browser_home": "about:blank",
  "window_size": [1400, 900]
}
```

- `claude_binary: null` → resolved via `$PATH`. Set to an absolute path to override.
- `window_size` is updated on window close.

### Runtime state persistence

Only `window_size` is persisted across app launches. No tab or session state is restored; the app always starts with an empty main pane.

## 10. Versioning

Semver, starting at **0.1.0**. Versioning lives in `pyproject.toml` and is re-exported as `persistent_claude_code.__version__`. The About dialog (`Ctrl+?`) shows the version.

Rationale for 0.x: this is a personal tool in active iteration; a stable 1.0 commitment is premature.

## 11. Installation & packaging

Arch Linux only for v1. Installation paths, in order of preference:

### 1. AUR (recommended)

```bash
yay -S persistent-claude-code-git
```

A `packaging/aur/PKGBUILD` in the repo declares the runtime dependencies (`python`, `python-gobject`, `gtk4`, `libadwaita`, `vte4`, `webkitgtk-6.0`) and installs sources, launcher, `.desktop` file, and icon into standard system locations. Updates come via `yay -Syu`.

### 2. Pre-built `.pkg.tar.zst` release asset

```bash
sudo pacman -U ./persistent-claude-code-0.1.0-1-any.pkg.tar.zst
```

CI (GitHub Actions) builds the `.pkg.tar.zst` from the PKGBUILD on each tagged release and attaches it to the GitHub Release. Full pacman integration, no AUR dependency.

### 3. `./install.sh` (dependency-free fallback)

A bash script that:

1. Verifies required binaries and Arch packages are present; prints a ready-to-copy `sudo pacman -S ...` line for any that are missing.
2. Verifies `python3 --version` is ≥ 3.14.
3. Copies `src/persistent_claude_code/` to `~/.local/share/persistent-claude-code/`.
4. Installs the `.desktop` file to `~/.local/share/applications/`.
5. Installs the icon to `~/.local/share/icons/hicolor/256x256/apps/`.
6. Installs a launcher at `~/.local/bin/persistent-claude-code` that `exec`s `python3 -m persistent_claude_code "$@"`.

`./uninstall.sh` is the exact inverse.

### Flatpak

Explicitly out of scope. Flatpak sandboxing makes spawning the host's `claude` binary awkward (requires `flatpak-spawn --host` plumbing and expanded host-filesystem portals), and the app targets a single user on a single Arch machine. Revisit if the project ever needs to be distributed more broadly.

### Dev ergonomics

`make run` invokes `python3 -m persistent_claude_code` from the source tree. No compile step; edit → restart.

## 12. README & docs

`README.md` at the repo root, covering:

- **Overview** — one-paragraph problem statement and what the app does.
- **Features (v1.0)** — explicit list: session browser, live status dots, embedded VTE terminal, embedded WebKit browser pane per tab, fuzzy filter, `+ New session` per project, session-ended placeholder with Resume, Libadwaita theming, keyboard shortcuts.
- **Screenshots** — placeholder; added after first working build.
- **Install** — leading with the `yay` one-liner, then `.pkg.tar.zst`, then `install.sh`.
- **Config** — the `config.json` keys and defaults.
- **Keybindings** — full table from section 4.
- **Roadmap (not in v1)** — full-text search, settings dialog, flatpak, per-session notes/tags, system tray, multi-window, multi-distro packaging.
- **License** — MIT.

## 13. Out of scope for v1

Explicitly deferred:

- Full-text search across all messages of all sessions.
- In-app settings dialog (config file only).
- Flatpak / Debian / RPM packaging; non-Arch support in general.
- Per-session notes, tags, or favourites.
- System tray integration.
- Multiple simultaneous tabs of the same session.
- CLI arg passthrough to `claude` (e.g. custom model flags).
- Multi-window support.
- Restoring open tabs across app restarts.

## 14. Open questions

None at spec approval.
