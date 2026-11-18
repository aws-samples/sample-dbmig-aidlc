"""Write the static review site (HTML + local CSS/JS, no remote resources)."""
from __future__ import annotations

import datetime as _dt
import difflib
import json
import shutil
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List

from . import render as r
from .collect import collect

ASSETS = Path(__file__).parent / "assets"
CSP = ("default-src 'none'; script-src 'self'; style-src 'self'; img-src 'self' data:; "
       "connect-src 'self'; base-uri 'none'; form-action 'none'")
NAV = [("index.html", "Overview"), ("gates.html", "Gates"), ("decisions.html", "Decisions"),
       ("code.html", "Code"), ("tests.html", "Tests"), ("documents.html", "Documents"),
       ("followups.html", "Follow-ups")]
_BADGE = {"approved": "ok", "applied": "ok", "pass": "ok", "match": "ok", "verified": "ok",
          "decided": "ok", "generated": "ok", "resolved": "ok", "done": "ok", "skipped": "muted",
          "empty": "muted", "withdrawn": "muted", "rejected": "bad", "failed": "bad", "fail": "bad",
          "mismatch": "bad", "needs_human": "bad", "error": "bad", "stale": "warn", "open": "warn",
          "pending": "warn", "converted": "info", "not run": "muted"}


def badge(s) -> str:
    s = "" if s is None else str(s)
    return f'<span class="b {_BADGE.get(s.lower(), "muted")}">{r.esc(s or "-")}</span>'


def page(title: str, body: str, data: Dict[str, Any], *, depth: int = 0, active: str = "") -> str:
    up = "../" * depth
    nav = "".join(f'<a class="{"on" if href == active else ""}" href="{up}{href}">{label}</a>'
                  for href, label in NAV)
    when = _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta http-equiv="Content-Security-Policy" content="{CSP}">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{r.esc(title)} — {r.esc(data['project'])}</title>
<link rel="stylesheet" href="{up}assets/app.css"></head>
<body><header><div class="brand">dbmig review · <b>{r.esc(data['project'])}</b>
<span class="sub">{r.esc(data.get('pair') or '')} · entry {r.esc(data['entry'])} ·
schemas {r.esc(', '.join(data['schemas']) or '-')}</span></div><nav>{nav}</nav></header>
<main>{body}</main>
<footer>Read-only view generated {when}. Approvals and decisions are recorded with
<code>./dbmig gate</code> / <code>./dbmig decision</code> (or in chat), not here.
This folder contains customer DDL, code and sample data: share it only with people allowed
to see them. AI-generated artifacts must be reviewed before use.</footer>
<script src="{up}assets/app.js"></script></body></html>
"""


def _table(headers: List[str], rows: List[List[str]], *, cls: str = "", fid: str = "") -> str:
    h = "".join(f"<th>{x}</th>" for x in headers)
    b = "".join("<tr>" + "".join(f"<td>{c}</td>" for c in row) + "</tr>" for row in rows)
    attr = f' id="{fid}"' if fid else ""
    return f'<div class="tw"><table class="grid {cls}"{attr}><thead><tr>{h}</tr></thead><tbody>{b}</tbody></table></div>'


def _filter_bar(target: str, statuses: List[str], extra: str = "") -> str:
    opts = "".join(f'<option value="{r.esc(s)}">{r.esc(s)}</option>' for s in statuses)
    return (f'<div class="bar"><input type="search" placeholder="Filter…" data-filter="{target}">'
            f'<select data-status="{target}"><option value="">all statuses</option>{opts}</select>'
            f"{extra}</div>")


# ---- pages ---------------------------------------------------------------------

def _overview(d) -> str:
    tl = []
    for g in d["gates"]:
        who = f"{r.esc(g.get('by'))} · {r.esc(g.get('at'))} · via {r.esc(g.get('via'))}" if g.get("by") else ""
        extra = ""
        if g["status"] == "stale":
            n = len(g.get("reasons") or [])
            extra = (f'<div class="why">Changed since approval ({n} item{"s" if n != 1 else ""}). '
                     f'<a href="gates.html#gate-{g["phase"]}">Why and how to fix</a></div>')
        elif g.get("waits_on"):
            extra = (f'<div class="why">Still approved, but the earlier gate '
                     f'<a href="gates.html#gate-{g["waits_on"]}">{r.esc(g["waits_on"])}</a> is stale; '
                     f're-approve that one first.</div>')
        tl.append(f'<div class="step {g["status"]}"><div class="t">{r.esc(g["title"])}</div>'
                  f'{badge(g["status"])}<div class="who">{who}</div>'
                  f'<div class="q">{r.esc(g["question"])}</div>{extra}</div>')
    counts = []
    for s in d["schemas"]:
        for kind in ("table", "code"):
            c = Counter(o["status"] for o in d["objects"] if o["schema"] == s and o["kind"] == kind)
            if c:
                counts.append([r.esc(s), kind, " ".join(f"{badge(k)} {v}" for k, v in sorted(c.items()))])
    nxt = d["next_gate"]
    nxt_html = (f"<p>Next gate: <b>{r.esc(nxt)}</b>.</p>" if nxt else "<p>All gates approved.</p>")
    blockers = next((g["blockers"] for g in d["gates"] if g["phase"] == nxt), []) if nxt else []
    if blockers:
        nxt_html += "<ul class='blockers'>" + "".join(f"<li>{r.esc(b)}</li>" for b in blockers) + "</ul>"
    open_dec = [x for x in d["decisions"] if x.get("status") == "open"]
    open_fu = [x for x in d["followups"] if x.get("status") == "open"]
    tests = [c for t in d["tests"] for c in t["cases"]]
    tc = Counter(c["status"] for c in tests)
    cards = [("Objects", len(d["objects"])), ("Open decisions", len(open_dec)),
             ("Open follow-ups", len(open_fu)),
             ("Test cases", f"{tc.get('pass', 0)}/{len(tests)} pass" if tests else "-")]
    card_html = "".join(f'<div class="card"><div class="n">{r.esc(v)}</div><div>{r.esc(k)}</div></div>'
                        for k, v in cards)
    note = "" if d["has_project_file"] else (
        "<p class='callout'>No <code>project.yaml</code> in this folder: gates are shown as open. "
        "Record approvals with <code>./dbmig gate approve</code>.</p>")
    return (f"<h1>Overview</h1>{note}<div class='timeline'>{''.join(tl)}</div>"
            f"<div class='cards'>{card_html}</div><h2>Where things stand</h2>{nxt_html}"
            + ("<h2>Units by status</h2>" + _table(["Schema", "Kind", "Status"], counts) if counts else ""))


def _gates(d) -> str:
    parts = ["<h1>Gates</h1>"]
    for g in d["gates"]:
        parts.append(f'<section class="gate" id="gate-{g["phase"]}"><h2>{r.esc(g["title"])} {badge(g["status"])}</h2>'
                     f'<p class="q">{r.esc(g["question"])}</p>')
        if g.get("by"):
            parts.append(f"<p>Last: <b>{r.esc(g['by'])}</b> at {r.esc(g['at'])} via {r.esc(g.get('via'))}"
                         + (f" — {r.esc(g['note'])}" if g.get("note") else "") + "</p>")
        if g["blockers"] and g["status"] != "approved":
            parts.append("<h3>Blockers</h3><ul class='blockers'>"
                         + "".join(f"<li>{r.esc(b)}</li>" for b in g["blockers"]) + "</ul>")
        if g["acknowledgements"] and g["status"] != "approved":
            parts.append("<h3>Needs acknowledgement</h3><ul>" + "".join(
                f"<li><code>{r.esc(k)}</code>: {n} open item(s)</li>" for k, n in g["acknowledgements"].items())
                + "</ul>")
        if g.get("acknowledged"):
            parts.append("<p>Acknowledged at approval: " + r.esc(", ".join(g["acknowledged"])) + "</p>")
        if g["status"] == "stale":
            parts.append("<div class='callout warn'><h3>Why is this gate stale?</h3>"
                         "<p>What was approved has changed since the approval:</p><ul>"
                         + "".join(f"<li><code>{r.esc(c)}</code></li>" for c in g["changes"][:200])
                         + f"</ul><p class='detail'>Usually: {r.esc(g.get('likely_cause'))}.</p>"
                         "<h3>How to fix</h3><ol>"
                         + "".join(f"<li>{r.inline(s)}</li>" for s in g.get("fix") or []) + "</ol></div>")
        if g.get("waits_on"):
            parts.append(f"<p class='callout'>Still approved, but the earlier gate "
                         f"<a href='#gate-{g['waits_on']}'>{r.esc(g['waits_on'])}</a> is stale. Re-approve "
                         "that one first; this gate keeps its approval unless its own files changed.</p>")
        if g["history"]:
            parts.append("<h3>History</h3>" + _table(
                ["When", "Status", "By", "Via", "Note", "Acknowledged"],
                [[r.esc(h.get("at")), badge(h.get("status")), r.esc(h.get("by")), r.esc(h.get("via")),
                  r.esc(h.get("note")), r.esc(", ".join(h.get("acknowledged") or []))]
                 for h in reversed(g["history"])]))
        parts.append("</section>")
    return "".join(parts)


def _decisions(d) -> str:
    rows = []
    for x in d["decisions"]:
        opts = "<ul class='opts'>" + "".join(
            f"<li class='{'chosen' if o.get('id') == x.get('choice') else ''}'><code>{r.esc(o.get('id'))}</code> "
            f"{r.esc(o.get('label'))}{' <i>(recommended)</i>' if o.get('recommended') else ''}</li>"
            for o in x.get("options") or []) + "</ul>"
        how = ""
        if x.get("status") != "open":
            how = f"{r.esc(x.get('by'))} via {r.esc(x.get('via'))}<br><small>{r.esc(x.get('at'))}</small>"
            if x.get("policy"):
                how += f"<br><span class='b info'>auto: policy {r.esc(x['policy'])}</span>"
        rows.append([f"<b>{r.esc(x.get('id'))}</b>", badge(x.get("status")),
                     f"{r.esc(x.get('phase'))}<br><code>{r.esc(x.get('kind'))}</code>",
                     r.esc(", ".join(x.get("objects") or [])),
                     f"{r.esc(x.get('question'))}{opts}"
                     + (f"<p class='detail'>{r.esc(x['detail'])}</p>" if x.get("detail") else ""),
                     how, r.esc(x.get("rationale"))])
    out = ["<h1>Decisions</h1>",
           "<p>Answer open decisions in chat or with <code>./dbmig decision answer &lt;id&gt; --choice &lt;option&gt;</code>.</p>",
           _filter_bar("dec", ["open", "decided", "withdrawn"]),
           _table(["Id", "Status", "Phase / kind", "Objects", "Question and options", "Answered", "Rationale"],
                  rows, fid="dec") if rows else "<p>No decisions recorded.</p>"]
    if d["policies"]:
        out.append("<h2>Questionnaire policies</h2>" + _table(
            ["Policy", "Choice", "Guidance", "By", "Source"],
            [[f"<code>{r.esc(k)}</code>",
              r.esc(p.get("label") or p.get("other") or p.get("choice"))
              + (" <i>(recommended default)</i>" if p.get("defaulted") else "")
              + (" <span class='b warn'>free text</span>" if p.get("needs_review") else ""),
              r.esc(p.get("guidance")), r.esc(p.get("by")), r.esc(p.get("source"))]
             for k, p in d["policies"].items() if isinstance(p, dict)]))
    for s, items in d["verify"].items():
        c = Counter(i.get("status") for i in items)
        out.append(f"<h2>DMS SC VERIFY ledger — {r.esc(s)} "
                   + " ".join(f"{badge(k)} {v}" for k, v in sorted(c.items(), key=lambda kv: str(kv[0]))) + "</h2>")
        out.append(_table(["Object", "Type", "Codes", "Status", "Method", "By", "When", "Note"],
                          [[r.esc(i.get("object")), r.esc(i.get("type")), r.esc(", ".join(map(str, i.get("codes") or []))),
                            badge(i.get("status")), r.esc(i.get("method")), r.esc(i.get("by")), r.esc(i.get("at")),
                            r.esc(i.get("note"))] for i in items]))
    return "".join(out)


def _code_index(d) -> str:
    rows = []
    for o in d["objects"]:
        rows.append([f'<a href="objects/{o["id"]}.html">{r.esc(o["name"])}</a>', r.esc(o["schema"]),
                     r.esc(o["type"]), badge(o["status"]),
                     badge(o["post_status"]) if o.get("post_status") else "",
                     r.esc(o.get("attempts") or ""), r.esc(o.get("disposition") or ""),
                     str(len(o["tests"])) if o["tests"] else "",
                     r.esc(", ".join(o["decisions"]))])
    statuses = sorted({o["status"] for o in d["objects"]})
    return ("<h1>Code browser</h1><p>Every table unit and code object. Open one to see the source and "
            "the converted code side by side.</p>" + _filter_bar("objs", statuses)
            + _table(["Object", "Schema", "Type", "Status", "Post-data", "Attempts", "DMS SC", "Tests",
                      "Decisions"], rows, fid="objs"))


def _diff(a: str, b: str, la: str, lb: str) -> str:
    lines = list(difflib.unified_diff((a or "").splitlines(), (b or "").splitlines(), la, lb, lineterm=""))
    if not lines:
        return "<p>No differences.</p>"
    out = []
    for ln in lines:
        cls = "add" if ln.startswith("+") and not ln.startswith("+++") else \
            "del" if ln.startswith("-") and not ln.startswith("---") else \
            "hunk" if ln.startswith("@@") else ""
        out.append(f'<span class="{cls or "ctx"}">{r.esc(ln) or " "}</span>')
    return '<pre class="code diff"><code>' + "".join(out) + "</code></pre>"


def _object(d, o, tests_by_id) -> str:
    meta = [("Schema", r.esc(o["schema"])), ("Type", r.esc(o["type"])), ("Status", badge(o["status"]))]
    if o.get("post_status"):
        meta.append(("Post-data (FK/triggers)", badge(o["post_status"])))
    if o.get("attempts"):
        meta.append(("Apply attempts", r.esc(o["attempts"])))
    if o.get("disposition"):
        meta.append(("DMS SC disposition", r.esc(o["disposition"])))
    for k, lbl in (("output_file", "Converted file"), ("prompt_file", "Prompt bundle")):
        if o.get(k):
            meta.append((lbl, f"<code>{r.esc(o[k])}</code>"))
    body = [f"<p><a href='../code.html'>← Code browser</a></p><h1>{r.esc(o['schema'])}.{r.esc(o['name'])}</h1>",
            "<dl class='meta'>" + "".join(f"<dt>{k}</dt><dd>{v}</dd>" for k, v in meta) + "</dl>"]
    for err_key, lbl in (("last_error", "Last apply error"), ("post_last_error", "Last post-data error")):
        if o.get(err_key):
            body.append(f"<h2>{lbl}</h2><pre class='err'>{r.esc(o[err_key])}</pre>")
    if o["action_items"]:
        body.append("<h2>DMS SC action items</h2>" + _table(
            ["Code", "Severity", "Topic", "Message"],
            [[r.esc(i.get("code")), badge(i.get("severity")), r.esc(i.get("topic")), r.esc(i.get("message"))]
             for i in o["action_items"]]))
    if o["decisions"]:
        decs = {x["id"]: x for x in d["decisions"]}
        body.append("<h2>Decisions</h2><ul>" + "".join(
            f"<li><a href='../decisions.html'>{r.esc(i)}</a> {badge(decs[i].get('status'))} "
            f"{r.esc(decs[i].get('question'))}</li>" for i in o["decisions"] if i in decs) + "</ul>")
    src_label = "Source" + (" (DMS SC snapshot)" if o.get("origin") == "dms_sc" else "")
    body.append('<div class="split"><div><h2>' + src_label + "</h2>"
                + (r.code_block(o["source"], "sql") if o.get("source") else "<p class='muted'>Source not found in the prompt bundle.</p>")
                + "</div><div><h2>Converted</h2>"
                + (r.code_block(o["converted"], "sql") if o.get("converted") else "<p class='muted'>Not converted yet.</p>")
                + "</div></div>")
    if o.get("dms_original") and o.get("converted") and o["dms_original"] != o["converted"]:
        body.append("<h2>Changes from the DMS SC output</h2>"
                    + _diff(o["dms_original"], o["converted"], "DMS SC", "current"))
    if o["notes"]:
        body.append("<h2>Conversion notes in the file</h2><ul>"
                    + "".join(f"<li><code>{r.esc(n)}</code></li>" for n in o["notes"]) + "</ul>")
    if o["log"]:
        body.append("<h2>Conversion log mentions</h2><div class='md'>"
                    + r.markdown("\n".join(f"- {x.lstrip('-* ')}" for x in o["log"])) + "</div>")
    for rt in o["retries"]:
        body.append(f"<details><summary>Retry prompt <code>{r.esc(rt['file'])}</code></summary>"
                    f"<pre class='code'>{r.esc(rt['text'] or '')}</pre></details>")
    if o["tests"]:
        body.append("<h2>Equivalence tests</h2>")
        for tid in o["tests"]:
            body.append(_test_block(tests_by_id[tid], depth=1))
    return "".join(body)


def _detail(det) -> str:
    if det is None:
        return ""
    if isinstance(det, dict):
        return "<table class='kv'>" + "".join(
            f"<tr><th>{r.esc(k)}</th><td>{_detail(v) if isinstance(v, (dict, list)) else r.esc(v)}</td></tr>"
            for k, v in det.items()) + "</table>"
    if isinstance(det, list):
        return "<br>".join(r.esc(json.dumps(x, default=str)) if not isinstance(x, str) else r.esc(x) for x in det)
    return r.esc(det)


def _sql_of(spec: Dict[str, Any]) -> str:
    if not spec:
        return ""
    parts = []
    for k in ("source_sql", "call_source", "target_sql", "call_target", "setup_source", "setup_target"):
        if spec.get(k):
            parts.append(f"<div class='lbl'>{r.esc(k)}</div><pre class='code'>{r.sql(str(spec[k]))}</pre>")
    for v in spec.get("verify") or []:
        if isinstance(v, dict):
            parts.append(f"<div class='lbl'>verify {r.esc(v.get('name'))}</div><pre class='code'>"
                         f"{r.sql(str(v.get('source_sql') or ''))}\n{r.sql(str(v.get('target_sql') or ''))}</pre>")
    return "".join(parts)


def _test_block(t, depth: int = 0) -> str:
    up = "../" * depth
    c = Counter(x["status"] for x in t["cases"])
    head = (f"<h3 id='{t['id']}'>{r.esc(t['schema'])}.{r.esc(t['name'])} <small>{r.esc(t.get('type'))}</small> "
            + " ".join(f"{badge(k)} {v}" for k, v in sorted(c.items()))
            + (" <span class='b warn'>LOW_COVERAGE</span>" if t["low_coverage"] else "")
            + (f" <a href='{up}objects/{t['object_id']}.html'>code</a>" if t.get("object_id") and depth == 0 else "")
            + "</h3>")
    notes = f"<p class='detail'>{r.esc(t['notes'])}</p>" if t.get("notes") else ""
    rows = [[r.esc(x["id"]), badge(x["status"]), r.esc(x.get("description") or ""),
             _sql_of(x.get("spec") or {}), _detail(x.get("detail"))] for x in t["cases"]]
    return (f"<div class='test' data-failed='{'1' if c.get('fail') or c.get('error') else '0'}'>"
            + head + notes + _table(["Case", "Result", "Description", "SQL", "Source vs target"], rows) + "</div>")


def _tests(d) -> str:
    out = ["<h1>Test browser</h1>"]
    for s, summ in d["summaries"].items():
        if summ:
            out.append(f"<p><b>{r.esc(s)}</b>: {summ.get('cases', 0)} cases · {summ.get('passed', 0)} passed · "
                       f"{summ.get('failed', 0)} failed · {summ.get('skipped', 0)} skipped · "
                       f"{summ.get('low_coverage_objects', 0)} low-coverage objects</p>")
    out.append('<div class="bar"><label><input type="checkbox" data-failed-only> failed only</label>'
               '<input type="search" placeholder="Filter objects…" data-filter-blocks=".test"></div>')
    out += [_test_block(t) for t in d["tests"]] or ["<p>No equivalence tests yet.</p>"]
    for s, rows in d["reconcile"].items():
        out.append(f"<h2>Row-count reconcile — {r.esc(s)}</h2>" + _table(
            ["Table", "Source rows", "Target rows", "Status"],
            [[r.esc(x.get("table")), r.esc(x.get("source_rows")), r.esc(x.get("target_rows")),
              badge(x.get("status"))] for x in rows]))
    return "".join(out)


def _documents(d) -> str:
    rows = [[f'<a href="docs/{x["id"]}.html">{r.esc(x["title"])}</a>', r.esc(x["phase"]),
             f"<code>{r.esc(x['path'])}</code>"] for x in d["docs"]]
    return "<h1>Documents</h1>" + _filter_bar("docs", []) + _table(["Title", "Phase", "File"], rows, fid="docs")


def _followups(d) -> str:
    rows = [[r.esc(i.get("ts")), r.esc(i.get("phase")), f"<code>{r.esc(i.get('kind'))}</code>",
             r.esc(i.get("object")), r.esc(i.get("detail")), badge(i.get("status")),
             r.esc(i.get("resolution") or "")] for i in d["followups"]]
    sts = sorted({str(i.get("status")) for i in d["followups"]})
    return ("<h1>Follow-up items</h1><p>From <code>follow-up.yaml</code>. Items that pass on a re-run "
            "become <i>resolved</i>; a person sets <i>done</i>.</p>" + _filter_bar("fu", sts)
            + (_table(["When", "Phase", "Kind", "Object", "Detail", "Status", "Resolution"], rows, fid="fu")
               if rows else "<p>No follow-up items.</p>"))


# ---- build ----------------------------------------------------------------------

def build(ws: Path, out: Path) -> Dict[str, Any]:
    d = collect(ws)
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    for sub in ("objects", "docs"):
        if (out / sub).exists():
            shutil.rmtree(out / sub)
        (out / sub).mkdir()
    if (out / "assets").exists():
        shutil.rmtree(out / "assets")
    shutil.copytree(ASSETS, out / "assets")

    def w(rel: str, title: str, body: str, depth: int = 0, active: str = "") -> None:
        (out / rel).write_text(page(title, body, d, depth=depth, active=active))

    w("index.html", "Overview", _overview(d), active="index.html")
    w("gates.html", "Gates", _gates(d), active="gates.html")
    w("decisions.html", "Decisions", _decisions(d), active="decisions.html")
    w("code.html", "Code", _code_index(d), active="code.html")
    w("tests.html", "Tests", _tests(d), active="tests.html")
    w("documents.html", "Documents", _documents(d), active="documents.html")
    w("followups.html", "Follow-ups", _followups(d), active="followups.html")
    tests_by_id = {t["id"]: t for t in d["tests"]}
    for o in d["objects"]:
        w(f"objects/{o['id']}.html", f"{o['schema']}.{o['name']}", _object(d, o, tests_by_id), depth=1,
          active="code.html")
    for doc in d["docs"]:
        w(f"docs/{doc['id']}.html", doc["title"],
          f"<p><a href='../documents.html'>← Documents</a> · <code>{r.esc(doc['path'])}</code></p>"
          f"<article class='md'>{r.markdown(doc['text'])}</article>", depth=1, active="documents.html")
    (out / "version.txt").write_text(_dt.datetime.now(_dt.timezone.utc).isoformat())
    return {"out": str(out), "objects": len(d["objects"]), "tests": len(d["tests"]), "docs": len(d["docs"]),
            "decisions": len(d["decisions"])}
