"""Safe HTML rendering for the review site: markdown, SQL, YAML.

Everything from the artifacts is escaped first; no raw HTML passes through (customer
DDL and documents can contain anything). Links are limited to http(s), relative paths
and anchors.
"""
from __future__ import annotations

import html
import re
from typing import List

_KEYWORDS = set("""
add all alter and as asc begin between body by call cascade case check column commit
constraint create cursor declare default delete desc distinct do drop else elsif end
exception exec execute exists foreign from function generated grant group having identity if
in index inner insert into is join key language left like limit loop merge not null of on
or order outer package plpgsql pragma primary procedure raise references replace return
returning returns right rollback schema select sequence set table then to trigger truncate
type union unique update using values view when where while with
""".split())

_SQL_TOKEN = re.compile(
    r"(?P<c1>--[^\n]*)|(?P<c2>/\*.*?\*/)|(?P<s>'(?:[^']|'')*')|(?P<q>\"(?:[^\"]|\"\")*\")"
    r"|(?P<w>[A-Za-z_][A-Za-z0-9_$#]*)|(?P<n>\b\d+(?:\.\d+)?\b)|(?P<o>.)",
    re.S)


def esc(s) -> str:
    return html.escape("" if s is None else str(s), quote=True)


def sql(text: str) -> str:
    """Highlighted SQL as escaped HTML (keywords, strings, comments, numbers)."""
    out: List[str] = []
    pos = 0
    for m in _SQL_TOKEN.finditer(text or ""):
        if m.start() > pos:
            out.append(esc(text[pos:m.start()]))
        tok = m.group(0)
        kind = m.lastgroup
        if kind in ("c1", "c2"):
            cls = "note" if tok.startswith("-- dbmig:") else "cm"
            out.append(f'<span class="{cls}">{esc(tok)}</span>')
        elif kind == "s":
            out.append(f'<span class="st">{esc(tok)}</span>')
        elif kind == "w" and tok.lower() in _KEYWORDS:
            out.append(f'<span class="kw">{esc(tok)}</span>')
        elif kind == "n":
            out.append(f'<span class="nu">{esc(tok)}</span>')
        else:
            out.append(esc(tok))
        pos = m.end()
    out.append(esc((text or "")[pos:]))
    return "".join(out)


def code_block(text: str, lang: str = "") -> str:
    body = sql(text) if lang.lower() in ("sql", "plsql", "tsql", "pgsql", "") and _looks_sql(text) \
        else esc(text)
    return f'<pre class="code"><code>{body}</code></pre>'


def _looks_sql(text: str) -> bool:
    return bool(re.search(r"\b(create|select|alter|insert|update|delete|begin|call)\b", text or "", re.I))


# ---- markdown ---------------------------------------------------------------

def _safe_url(u: str) -> str:
    u = u.strip()
    if re.match(r"^(https?://|#|\./|\.\./|[\w./-]+$)", u) and not u.lower().startswith(("javascript:", "data:")):
        return u
    return "#"


def inline(text: str) -> str:
    """Inline markdown on already-unescaped text: code, bold, italic, links."""
    parts = re.split(r"(`[^`]+`)", text)
    out = []
    for p in parts:
        if p.startswith("`") and p.endswith("`") and len(p) >= 2:
            out.append(f"<code>{esc(p[1:-1])}</code>")
            continue
        s = esc(p)
        s = re.sub(r"\[([^\]]+)\]\(([^)\s]+)\)",
                   lambda m: f'<a href="{esc(_safe_url(html.unescape(m.group(2))))}">{m.group(1)}</a>', s)
        s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
        s = re.sub(r"(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])", r"<em>\1</em>", s)
        s = re.sub(r"(?<![\w])_(?!\s)(.+?)(?<!\s)_(?![\w])", r"<em>\1</em>", s)
        out.append(s)
    return "".join(out)


def _table(rows: List[str]) -> str:
    def cells(r):
        r = r.strip()
        if r.startswith("|"):
            r = r[1:]
        if r.endswith("|") and not r.endswith("\\|"):
            r = r[:-1]
        return [c.strip().replace("\\|", "|") for c in re.split(r"(?<!\\)\|", r)]
    head = cells(rows[0])
    body = [cells(r) for r in rows[2:]]
    h = "".join(f"<th>{inline(c)}</th>" for c in head)
    b = "".join("<tr>" + "".join(f"<td>{inline(c)}</td>" for c in r) + "</tr>" for r in body)
    return f'<div class="tw"><table class="md"><thead><tr>{h}</tr></thead><tbody>{b}</tbody></table></div>'


def markdown(text: str) -> str:
    text = re.sub(r"<!--.*?-->", "", text or "", flags=re.S)
    lines = text.splitlines()
    out: List[str] = []
    i = 0
    para: List[str] = []

    def flush():
        if para:
            out.append("<p>" + inline(" ".join(x.strip() for x in para)) + "</p>")
            para.clear()

    while i < len(lines):
        ln = lines[i]
        st = ln.strip()
        if st.startswith("```"):
            flush()
            lang = st[3:].strip()
            buf = []
            i += 1
            while i < len(lines) and not lines[i].strip().startswith("```"):
                buf.append(lines[i])
                i += 1
            out.append(code_block("\n".join(buf), lang))
            i += 1
            continue
        m = re.match(r"^(#{1,6})\s+(.*)$", st)
        if m:
            flush()
            n = len(m.group(1))
            slug = re.sub(r"[^\w-]+", "-", m.group(2).lower()).strip("-")
            out.append(f'<h{n} id="{esc(slug)}">{inline(m.group(2))}</h{n}>')
            i += 1
            continue
        if re.match(r"^(-{3,}|\*{3,}|_{3,})$", st):
            flush()
            out.append("<hr>")
            i += 1
            continue
        if st.startswith(">"):
            flush()
            buf = []
            while i < len(lines) and lines[i].strip().startswith(">"):
                buf.append(re.sub(r"^\s*>\s?", "", lines[i]))
                i += 1
            inner = "\n".join(buf)
            cls = "callout warn" if "AI-GENERATED" in inner.upper() else "callout"
            out.append(f'<blockquote class="{cls}">{markdown(inner)}</blockquote>')
            continue
        if st.startswith("|") and i + 1 < len(lines) and re.match(r"^\s*\|?\s*:?-{2,}", lines[i + 1]):
            flush()
            rows = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                rows.append(lines[i])
                i += 1
            out.append(_table(rows))
            continue
        if re.match(r"^\s*([-*+]|\d+[.)])\s+", ln):
            flush()
            html_list, i = _list(lines, i)
            out.append(html_list)
            continue
        if not st:
            flush()
            i += 1
            continue
        para.append(ln)
        i += 1
    flush()
    return "\n".join(out)


def _list(lines: List[str], i: int):
    first = re.match(r"^(\s*)([-*+]|\d+[.)])\s+", lines[i])
    base = len(first.group(1))
    ordered = first.group(2)[0].isdigit()
    items: List[str] = []
    cur: List[str] = []
    while i < len(lines):
        ln = lines[i]
        m = re.match(r"^(\s*)([-*+]|\d+[.)])\s+(.*)$", ln)
        if m and len(m.group(1)) == base:
            if cur:
                items.append("\n".join(cur))
            cur = [m.group(3)]
            i += 1
            continue
        if ln.strip() and (len(ln) - len(ln.lstrip())) > base:
            cur.append(ln[base + 2:] if len(ln) > base + 2 else ln.strip())
            i += 1
            continue
        if not ln.strip() and i + 1 < len(lines) and re.match(rf"^\s{{{base + 1},}}\S", lines[i + 1] or ""):
            i += 1
            continue
        break
    if cur:
        items.append("\n".join(cur))
    tag = "ol" if ordered else "ul"
    body = []
    for it in items:
        head, *rest = it.split("\n")
        sub = "\n".join(rest)
        inner = inline(head)
        if sub.strip():
            if re.match(r"^\s*([-*+]|\d+[.)])\s+", sub):
                inner += markdown(sub)
            else:
                inner += " " + inline(" ".join(x.strip() for x in rest))
        body.append(f"<li>{inner}</li>")
    return f"<{tag}>" + "".join(body) + f"</{tag}>", i
