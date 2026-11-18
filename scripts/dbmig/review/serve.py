"""Optional loopback server and file watcher for ``dbmig review``.

Binds 127.0.0.1 only, serves only the generated folder, answers GET/HEAD only, and
rejects requests whose Host header is not this loopback address (DNS-rebinding guard).
"""
from __future__ import annotations

import functools
import os
import threading
import time
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Callable, Optional

HOST = "127.0.0.1"


class _Handler(SimpleHTTPRequestHandler):
    allowed_hosts: set = set()

    def _host_ok(self) -> bool:
        return (self.headers.get("Host") or "") in self.allowed_hosts

    def _deny(self, code: int, msg: str) -> None:
        self.send_error(code, msg)

    def do_GET(self):  # noqa: N802
        if not self._host_ok():
            return self._deny(403, "host not allowed")
        if ".." in self.path.split("?")[0].split("/"):
            return self._deny(400, "bad path")
        return super().do_GET()

    def do_HEAD(self):  # noqa: N802
        if not self._host_ok():
            return self._deny(403, "host not allowed")
        return super().do_HEAD()

    def _method_not_allowed(self):
        self._deny(405, "read-only")

    do_POST = do_PUT = do_DELETE = do_PATCH = do_OPTIONS = _method_not_allowed  # noqa: N815

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        super().end_headers()

    def log_message(self, fmt, *args):  # quiet
        pass


def make_server(root: Path, port: int = 0) -> ThreadingHTTPServer:
    handler = functools.partial(_Handler, directory=str(root))
    srv = ThreadingHTTPServer((HOST, port), handler)
    p = srv.server_address[1]
    _Handler.allowed_hosts = {f"{HOST}:{p}", f"localhost:{p}"}
    return srv


def _snapshot(ws: Path, out: Path) -> float:
    latest = 0.0
    out_r = out.resolve()
    for dirpath, dirnames, filenames in os.walk(ws):
        d = Path(dirpath).resolve()
        if d == out_r or out_r in d.parents:
            dirnames[:] = []
            continue
        dirnames[:] = [x for x in dirnames if not x.startswith(".")]
        for f in filenames:
            try:
                latest = max(latest, (Path(dirpath) / f).stat().st_mtime)
            except OSError:
                pass
    return latest


def watch(ws: Path, out: Path, rebuild: Callable[[], None], interval: float = 2.0,
          stop: Optional[threading.Event] = None) -> None:
    last = _snapshot(ws, out)
    while not (stop and stop.is_set()):
        time.sleep(interval)
        cur = _snapshot(ws, out)
        if cur != last:
            last = cur
            try:
                rebuild()
            except Exception as exc:  # noqa: BLE001 - keep watching
                print(f"[WARN] rebuild failed: {exc}")
