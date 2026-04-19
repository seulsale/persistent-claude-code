from __future__ import annotations

from gi.repository import Gtk, WebKit


class BrowserPane(Gtk.Box):
    __gtype_name__ = "PCCBrowserPane"

    def __init__(self, home_url: str) -> None:
        super().__init__(orientation=Gtk.Orientation.VERTICAL)

        self._home_url = home_url

        toolbar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4, margin_top=4, margin_bottom=4, margin_start=4, margin_end=4)

        self._back = Gtk.Button.new_from_icon_name("go-previous-symbolic")
        self._forward = Gtk.Button.new_from_icon_name("go-next-symbolic")
        self._reload = Gtk.Button.new_from_icon_name("view-refresh-symbolic")
        self._url_entry = Gtk.Entry(hexpand=True)
        self._url_entry.set_placeholder_text("about:blank")

        toolbar.append(self._back)
        toolbar.append(self._forward)
        toolbar.append(self._reload)
        toolbar.append(self._url_entry)

        self.webview = WebKit.WebView()
        self.webview.set_vexpand(True)
        self.webview.load_uri(home_url)

        self.append(toolbar)
        self.append(self.webview)

        self._back.connect("clicked", lambda *_: self.webview.go_back())
        self._forward.connect("clicked", lambda *_: self.webview.go_forward())
        self._reload.connect("clicked", lambda *_: self.webview.reload())
        self._url_entry.connect("activate", self._on_url_activate)

        self.webview.connect("load-changed", self._sync_url)

    def _on_url_activate(self, entry: Gtk.Entry) -> None:
        text = entry.get_text().strip()
        if not text:
            return
        if not text.startswith(("http://", "https://", "about:", "file://")):
            text = "https://" + text
        self.webview.load_uri(text)

    def _sync_url(self, _webview, _evt) -> None:
        uri = self.webview.get_uri()
        if uri:
            self._url_entry.set_text(uri)
