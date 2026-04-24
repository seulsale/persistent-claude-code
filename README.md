# Persistent Claude Code

A local GTK4 / GNOME desktop app for browsing and resuming Claude Code sessions without opening a terminal, navigating to the project, and running `claude --resume <id>`.

## Features

- Sidebar browser of all sessions under `~/.claude/projects/`, grouped by project, sorted by most-recent activity.
- Fuzzy filter across project paths and session titles (`Ctrl+K`). Press `Enter` in the search box to launch the first visible session.
- One-click resume: each session opens in its own tab running `claude --resume <id>` inside an embedded VTE terminal.
- `+ New session` row per project for starting a fresh `claude` in that cwd.
- Embedded WebKit browser pane per tab (`Ctrl+Shift+B`), with back/forward/reload and a URL bar.
- `--open-url URL` flag routes `xdg-open` / `$BROWSER` requests from inside `claude` into the current tab's browser pane. (Playwright MCP still launches its own Chromium — that's a separate process we can't intercept.)
- Live status dots in the sidebar for sessions running in the app: 🟢 working, 🟡 waiting, ⚪ idle.
- "Session ended" placeholder with **Resume** and **Close** buttons when `claude` exits.
- Nord-themed VTE terminal with JetBrains Mono and 8 px padding (Ghostty-lookalike).
- Libadwaita theming follows system light/dark.
- **Persistent state across restarts:** open tabs reopen dormant (title preserved, `claude` not spawned until you click **Resume**), and expanded sidebar folders are remembered. Window size is also persisted.

Per-release details live under [`changelog/`](changelog/).

## Install

Arch Linux only.

### Recommended — AUR

```bash
yay -S persistent-claude-code-git
```

### From a GitHub Release (pacman)

Download the `.pkg.tar.zst` asset from the latest release, then:

```bash
sudo pacman -U ./persistent-claude-code-git-*.pkg.tar.zst
```

### From source

```bash
git clone https://github.com/seulsale/persistent-claude-code.git
cd persistent-claude-code
./install.sh
# to undo:
./uninstall.sh
```

## Requirements

Arch packages (installed automatically by the PKGBUILD / checked by `install.sh`):

- `python` (3.14+)
- `python-gobject`
- `gtk4`
- `libadwaita`
- `vte4`
- `webkitgtk-6.0`
- `ttf-jetbrains-mono`

And the [`claude`](https://docs.anthropic.com/claude/docs/claude-code) CLI installed and on `$PATH`.

## Configuration

Config lives at `~/.config/persistent-claude-code/config.json` (created on first launch with defaults). There is no in-app settings dialog in v1 — edit the file directly.

| Key | Default | Purpose |
| --- | --- | --- |
| `terminal_font` | `"JetBrains Mono 11"` | Pango font string for the VTE terminal. |
| `terminal_scrollback` | `10000` | Terminal scrollback line count. |
| `claude_binary` | `null` | Absolute path to `claude`; `null` resolves via `$PATH`. |
| `browser_home` | `"about:blank"` | Initial URL for a newly-opened browser pane. |
| `window_size` | `[1400, 900]` | Window size; auto-persisted on close. |
| `open_tabs` | `[]` | Tabs to restore on next launch; auto-persisted on close. |
| `expanded_projects` | `[]` | Sidebar folders expanded at close; auto-persisted. |

## Keybindings

| Shortcut | Action |
| --- | --- |
| `Ctrl+K` | Focus sidebar search |
| `Ctrl+T` | Focus `+ New session` of the first project |
| `Ctrl+W` | Close current tab |
| `Ctrl+Tab` / `Ctrl+Shift+Tab` | Cycle tabs forward / backward |
| `Ctrl+Shift+B` | Toggle the browser pane in the current tab |
| `Ctrl+?` | About dialog |

All shortcuts use the capture phase so VTE doesn't swallow them while the terminal has focus.

## Browser integration

When the app is running, `persistent-claude-code --open-url <URL>` forwards the URL to the primary instance's currently-selected tab and displays it in that tab's browser pane. The `BROWSER` environment variable is set to `persistent-claude-code --open-url` for every spawned `claude` process, so any `xdg-open` call inside Claude lands in the embedded pane. MCP servers that spawn their own browsers (e.g. Playwright) are unaffected.

If no session tab is currently selected when the URL arrives, a toast suggests opening one first.

## Roadmap

- Full-text search across all messages of all sessions.
- In-app settings dialog.
- Per-session notes, tags, or favourites.
- System tray integration.
- Multi-distro packaging (Flatpak, `.deb`, `.rpm`).
- Multiple windows.

## Changelog

Per-version details live under [`changelog/`](changelog/):

- [v0.1.3](changelog/v0.1.3.md) — sidebar redesign, tab persistence, AUR publish workflow.
- [v0.1.2](changelog/v0.1.2.md) — re-tag of v0.1.1 (no functional changes).
- [v0.1.1](changelog/v0.1.1.md) — fix `claude` lookup when launched from desktop entry.
- [v0.1.0](changelog/v0.1.0.md) — initial release.

## License

MIT — see [LICENSE](LICENSE).
