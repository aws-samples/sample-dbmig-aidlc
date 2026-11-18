"""Review site: build from the sample runs, escaping, CSP, loopback server."""
from __future__ import annotations

import http.client
import re
import threading
from pathlib import Path

import pytest
import yaml

from dbmig.review import build as rb, render, serve as rs
from dbmig.review.collect import collect

REPO = Path(__file__).resolve().parents[2]
SAMPLES = sorted(p for p in REPO.glob("sample-run-*") if p.is_dir())


@pytest.mark.parametrize("sample", SAMPLES, ids=lambda p: p.name)
def test_build_sample(sample, tmp_path):
    before = {p: p.stat().st_mtime for p in sample.rglob("*") if p.is_file()}
    res = rb.build(sample, tmp_path)
    assert (tmp_path / "index.html").exists()
    d = collect(sample)
    for o in d["objects"]:
        assert (tmp_path / "objects" / f"{o['id']}.html").exists()
        assert o["source"], o["name"]                     # source DDL extracted
    assert res["tests"] == len(d["tests"]) and sum(len(t["cases"]) for t in d["tests"]) > 0
    assert all(c["status"] != "not run" for t in d["tests"] for c in t["cases"])
    assert (tmp_path / "docs").iterdir()
    for f in tmp_path.rglob("*.html"):
        h = f.read_text()
        assert "Content-Security-Policy" in h
        assert not re.search(r"<(script|link)[^>]+(src|href)=\"https?://", h), f
    # building never writes into the (committed) sample folder
    after = {p: p.stat().st_mtime for p in sample.rglob("*") if p.is_file()}
    assert before == after


def test_markdown_escapes_raw_html_and_unsafe_links():
    out = render.markdown("# T\n\n<script>alert(1)</script> [x](javascript:alert(1)) **b**\n\n"
                          "| a | b |\n|---|---|\n| <img src=x onerror=1> | `c` |\n\n"
                          "> ⚠ **AI-GENERATED — VALIDATE BEFORE USE.** text\n\n```sql\nselect '<b>'\n```")
    assert "<script>" not in out and "&lt;script&gt;" in out
    assert 'href="#"' in out and "<img" not in out
    assert "<strong>b</strong>" in out and "callout warn" in out and "&lt;b&gt;" in out


def test_sql_highlight_escapes():
    h = render.sql("SELECT '<x>' FROM t -- dbmig: note\n/* c */")
    assert '<span class="kw">SELECT</span>' in h and "&lt;x&gt;" in h
    assert 'class="note"' in h and 'class="cm"' in h


def test_object_page_escapes_customer_ddl(tmp_path):
    ws = tmp_path / "w"
    (ws / "02-construction" / "ddl").mkdir(parents=True)
    (ws / "02-construction" / "ddl" / "t.sql").write_text("CREATE TABLE t (c text DEFAULT '</pre><script>x</script>');")
    (ws / "02-construction" / "manifest-APP.yaml").write_text(yaml.safe_dump(
        {"units": [{"name": "T", "status": "applied", "output_file": "ddl/t.sql"}]}))
    rb.build(ws, tmp_path / "out")
    page = next((tmp_path / "out" / "objects").glob("*.html")).read_text()
    assert "<script>x</script>" not in page and "&lt;/pre&gt;&lt;script&gt;" in page


@pytest.fixture()
def server(tmp_path):
    (tmp_path / "index.html").write_text("ok")
    srv = rs.make_server(tmp_path, 0)
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    yield srv.server_address
    srv.shutdown()


def _req(addr, method="GET", path="/index.html", host=None):
    c = http.client.HTTPConnection(*addr, timeout=5)
    c.putrequest(method, path, skip_host=True)
    c.putheader("Host", host or f"{addr[0]}:{addr[1]}")
    c.endheaders()
    r = c.getresponse()
    return r.status


def test_server_loopback_only_and_read_only(server):
    assert server[0] == "127.0.0.1"
    assert _req(server) == 200
    assert _req(server, host=f"evil.example:{server[1]}") == 403
    assert _req(server, method="POST") == 405
    assert _req(server, path="/../../etc/passwd") in (400, 404)
