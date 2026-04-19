from __future__ import annotations

import sys


def run() -> int:
    import gi
    gi.require_version("Gtk", "4.0")
    gi.require_version("Adw", "1")
    gi.require_version("Vte", "3.91")
    gi.require_version("WebKit", "6.0")

    from persistent_claude_code.app import App

    app = App()
    return app.run(sys.argv)
