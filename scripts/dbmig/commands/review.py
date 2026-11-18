"""``dbmig review`` — build the read-only review site for a migration folder.

    ./dbmig review --project P [--open] [--watch] [--serve [--port N]]
    ./dbmig review --dir sample-run-oracle-to-pg --out /tmp/review

Output defaults to migrations/<P>/review/ (git-ignored). For a folder outside the
migrations root (e.g. a committed sample run) it defaults to a new temporary folder,
so a generated site is never written into tracked files.
"""
from __future__ import annotations

import tempfile
import threading
import webbrowser
from pathlib import Path

from .. import config, console
from ..project import resolve_dir
from ..review import build as rb, serve as rs


def _out_dir(args, ws: Path) -> Path:
    if args.out:
        return Path(args.out).expanduser().resolve()
    root = config.migrations_root().resolve()
    if root in ws.parents:
        return ws / "review"
    return Path(tempfile.mkdtemp(prefix="dbmig-review-"))


def run(args) -> int:
    ws = resolve_dir(args)
    if not ws.is_dir():
        console.err(f"no migration folder at {ws}")
        return 2
    out = _out_dir(args, ws)

    def rebuild():
        res = rb.build(ws, out)
        console.ok(f"review site: {res['objects']} object(s), {res['tests']} test object(s), "
                   f"{res['docs']} document(s), {res['decisions']} decision(s) -> {out}/index.html")

    rebuild()
    console.info("The site contains customer DDL, code and sample data; share it only with "
                 "people allowed to see them.")
    url = (out / "index.html").as_uri()
    srv = None
    if args.serve:
        srv = rs.make_server(out, args.port)
        url = f"http://{rs.HOST}:{srv.server_address[1]}/index.html"
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        console.info(f"serving read-only on {url} (loopback only; Ctrl-C to stop)")
    if args.open:
        webbrowser.open(url)
    if args.watch or args.serve:
        try:
            if args.watch:
                console.info("watching for changes every 2 s")
                rs.watch(ws, out, rebuild)
            else:
                threading.Event().wait()
        except KeyboardInterrupt:
            pass
        finally:
            if srv:
                srv.shutdown()
    return 0
