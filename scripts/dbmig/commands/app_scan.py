"""``dbmig app-scan`` — deterministic, read-only pre-scan for app modernization.

The assistant used to walk, grep and read the whole application during Inception;
on a 1,000+ file code base that means reading every file into context. This
command does the mechanical part locally in one pass (see ``dbmig.appscan`` for
the language/framework coverage) and writes:

``migrations/<project>/05-application/01-assessment/app-scan.yaml`` (full index) and
``app-scan.md`` (compact: counts, frameworks, obligations, and the FLAGGED files —
open only those). Nothing is edited; the database is only read (catalog).
"""
from __future__ import annotations

import re
from collections import Counter
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import yaml

from .. import appscan as A
from .. import config, console

DEFAULT_TERMS = {
    "oracle": ["SYSDATE", "SYSTIMESTAMP", "NVL", "NVL2", "DECODE", "DUAL", "ROWNUM",
               "CONNECT BY", "(+)", "MINUS", "LISTAGG", "TO_DATE", "TO_CHAR", "TRUNC",
               "ADD_MONTHS", "MONTHS_BETWEEN", "NEXTVAL", "CONTAINS(", "CATSEARCH",
               "SCORE(", "/*+", "FETCH FIRST", "REGEXP_", "ROWID", "SUBSTR", "INSTR"],
    "sqlserver": ["GETDATE", "GETUTCDATE", "SYSDATETIME", "ISNULL", "TOP ", "TOP(",
                  "@@IDENTITY", "@@ROWCOUNT", "SCOPE_IDENTITY", "LEN(", "MERGE", "CROSS APPLY",
                  "OUTER APPLY", "NOLOCK", "DATEADD", "DATEDIFF", "DATEPART", "CONVERT(",
                  "NEWID", "[dbo]", "dbo.", "IIF(", "CHARINDEX", "STUFF(", "FOR XML",
                  "OFFSET", "NVARCHAR", "+ '"],
}


def _load_terms(pair: str) -> List[str]:
    root = config.find_repo_root()
    try:
        cfg = yaml.safe_load((root / f"engines/{pair}/app/app-config.yaml").read_text()) or {}
    except Exception:  # noqa: BLE001
        cfg = {}
    return list(cfg.get("scan_terms") or DEFAULT_TERMS.get(pair.split("-to-")[0], []))


def _target_columns(schema: Optional[str]) -> Tuple[Dict[Tuple[str, str], str], Optional[str], str]:
    """{(table_lower, column_lower): data_type}, reason-if-unavailable, schema used."""
    try:
        from .. import engines
        from ..connections import load_pair
        pair = load_pair()
        if "target" not in pair:
            return {}, "no target connection configured", ""
        tgt = engines.get_target_engine(pair)
    except Exception as exc:  # noqa: BLE001
        return {}, f"target not available: {exc}", ""
    try:
        sch = (schema or tgt.model.extra.get("default_schema") or tgt.model.database
               or "public")
        _, rows = tgt.fetch(
            "SELECT table_name, column_name, data_type FROM information_schema.columns "
            "WHERE table_schema = %s", (sch,))
        cols = {(str(r[0]).lower(), str(r[1]).lower()): str(r[2]) for r in rows}
        return cols, (None if cols else f"no columns in target schema '{sch}'"), sch
    except Exception as exc:  # noqa: BLE001
        return {}, f"catalog read failed: {exc}", ""
    finally:
        tgt.close()


def scan(app: Path, pair: str, target_schema: Optional[str], check_target: bool = True) -> dict:
    files, leftovers, skipped = A.walk(app)
    term_res = [(t, A._term_re(t)) for t in _load_terms(pair)]
    sites = {k: [] for k in ("sql", "routine", "error", "resultset", "conn_code", "config",
                             "db_scripts")}
    fw_hits: Dict[str, set] = {}
    entities: List[dict] = []
    cs_classes: Dict[str, dict] = {}
    dbsets: Dict[str, str] = {}
    fluent: Dict[str, dict] = {}
    by_ext, scanned = Counter(), 0
    for p in files:
        rel = str(p.relative_to(app))
        ext = p.suffix.lower()
        by_ext[ext or p.name] += 1
        try:
            if p.stat().st_size > A.MAX_BYTES:
                continue
            text = p.read_text(errors="ignore")
        except OSError:
            continue
        scanned += len(text)
        lang = A.LANG.get(ext, "")
        if lang == "js" and not A.JS_DB_RE.search(text):
            continue                               # front-end JS: no DB access
        for name, rx in A.FRAMEWORK_RES:
            if A.CONFIG_NAMES.search(p.name) and not p.name.endswith(
                    (".csproj", "pom.xml", ".gradle", ".kts", "package.json", ".txt", ".toml")):
                break                              # frameworks come from code/build files
            if rx.search(text):
                fw_hits.setdefault(name, set()).add(rel)
        if A.CONFIG_NAMES.search(p.name):
            for i, line in enumerate(text.splitlines(), 1):
                s = line.strip()
                if s.startswith(("#", "//", "<!--")):
                    continue
                if A.SECRET_RE.search(s) and "${" not in s and "{{" not in s and \
                        not re.search(r"[=:]\s*[\"']?\s*$", s):
                    sites["config"].append({"file": rel, "line": i, "kind": "plaintext-secret",
                                            "text": A.SECRET_RE.sub(r"\1***", s)[:200]})
                elif A.CONFIG_KEYS_RE.search(s):
                    sites["config"].append({"file": rel, "line": i,
                                            "text": A.SECRET_RE.sub(r"\1***", s)[:200]})
            if ext not in (".xml",):
                continue
        # Embedded SQL
        if lang == "sql":
            # SQL scripts shipped with the app (DDL/seed/admin) are source-engine
            # artifacts: report the file once, don't list its internals as sites.
            hits = sorted({t for t, rx in term_res if rx.search(text)})
            sites["db_scripts"].append({"file": rel, "constructs": hits,
                                        "bytes": len(text)})
            continue
        elif lang == "xml":
            cands = [(A._line(text, m.start()), m.group(0)) for m in re.finditer(
                r"<(select|insert|update|delete|sql|procedure|named-native-query|sql-query|query)\b.*?</\1>",
                text, re.S | re.I)]
        elif lang == "prisma":
            cands = []
        else:
            cands = A.string_literals(text, lang)
        # Files that build SQL: fragments (StringBuilder.append("AND x > TO_DATE(...)"),
        # conditional WHERE pieces) carry no SELECT keyword but are still SQL — in
        # such files a literal with a construct hit is reported as a Tier-3 fragment.
        builds_sql = lang not in ("sql", "xml") and any(
            A.SQL_HINT_RE.search(lit) for _, lit in cands)
        tq = A.TEXT_QUERY_RE.get(pair.split("-to-")[0])
        if tq and lang not in ("sql", "xml"):
            for ln, lit in cands:
                m = tq.search(lit)
                if m and len(lit) < 200 and not A.SQL_HINT_RE.search(lit) and \
                        re.search(r"\(|\$|!", m.group(0)):
                    sites["sql"].append({"file": rel, "line": ln, "fragment": True,
                                         "constructs": ["full-text query syntax: " + m.group(0).strip()],
                                         "sql": lit[:300]})
        for ln, lit in cands:
            fragment = False
            if lang not in ("sql", "xml") and not A.SQL_HINT_RE.search(lit):
                if not builds_sql:
                    continue
                fragment = True
            hits = sorted({t for t, rx in term_res if rx.search(lit)})
            if fragment and not hits:
                continue
            site = {"file": rel, "line": ln, "constructs": hits,
                    "sql": " ".join(lit.split())[:300]}
            if fragment:
                site["fragment"] = True    # Tier 3: reconstruct the full statement
            sites["sql"].append(site)
        cmt = "#" if lang in ("py", "rb") else "//"
        for i, line in enumerate(text.splitlines(), 1):
            if line.lstrip().startswith((cmt, "*", "/*", "<!--")):
                continue
            for key, rx in (("routine", A.ROUTINE_RE), ("error", A.ERROR_RE),
                            ("resultset", A.RESULTSET_RE), ("conn_code", A.CONN_CODE_RE)):
                if rx.search(line):
                    sites[key].append({"file": rel, "line": i,
                                       "text": A.SECRET_RE.sub(r"\1***", line.strip())[:200]})
        # Mappings
        if lang == "java":
            entities += A.extract_jpa(text, rel)
        elif lang == "cs":
            cs_classes.update(A.cs_classes(text, rel))
            for m in re.finditer(r"DbSet<(\w+)>\s+(\w+)", text):
                dbsets[m.group(1)] = m.group(2)
            for k, v in A.ef_model_config(text).items():
                fluent.setdefault(k, {"props": {}})
                fluent[k]["props"].update(v.get("props", {}))
                for kk in ("table", "schema"):
                    if v.get(kk):
                        fluent[k][kk] = v[kk]
        elif lang == "py":
            entities += A.extract_python(text, rel)
        elif lang == "js":
            entities += A.extract_js(text, rel)
        elif lang == "prisma":
            entities += A.extract_prisma(text, rel)
    if dbsets or fluent:
        entities += A.resolve_ef(cs_classes, dbsets, fluent)

    cols, reason, sch = ({}, "skipped (--no-target)", "") if not check_target \
        else _target_columns(target_schema)
    target_tables = {t for t, _ in cols}
    rows = []
    for e in entities:
        tlow = e["table"].lower()
        table_found = not cols or tlow in target_tables
        case_issue = (cols and e.get("table_quoted") and e["table"] != tlow and table_found)
        for f in e["fields"]:
            tt = cols.get((tlow, str(f["column"]).lower())) if cols else None
            r = {"orm": e["orm"], "entity": e["class"], "field": f["field"],
                 "type": f.get("java_type"), "table": e["table"], "column": f["column"],
                 "target_type": tt, "file": f.get("decl_file") or e["file"], "line": f["line"]}
            ob = A.obligation(f, tt, e["orm"])
            if ob:
                r["obligation"] = ob
            if cols and not f.get("relation"):
                if not table_found:
                    r["issue"] = f"table `{e['table']}` not in target schema `{sch}`"
                elif tt is None:
                    r["issue"] = "column not in target (name / naming-strategy drift?)"
                elif (f.get("quoted") or e["orm"] == "EF Core" and not f.get("explicit", True)) \
                        and str(f["column"]) != str(f["column"]).lower():
                    r["issue"] = ("identifier case: the ORM quotes "
                                  f"\"{f['column']}\" but the target folded it to "
                                  f"{str(f['column']).lower()} — fold names in the model")
            if case_issue and "issue" not in r:
                r["issue"] = (f"identifier case: table \"{e['table']}\" is quoted by the ORM; "
                              f"target has {tlow} — fold names in the model")
            rows.append(r)
    return {
        "app_dir": str(app), "pair": pair,
        "files_in_scope": len(files), "bytes_scanned": scanned,
        "files_by_type": dict(by_ext.most_common()),
        "excluded_dirs": dict(skipped),
        "leftovers": [str(x.relative_to(app)) for x in leftovers],
        "frameworks": {k: sorted(v)[:20] for k, v in sorted(fw_hits.items())},
        "sites": sites,
        "entities": [{"orm": e["orm"], "class": e["class"], "table": e["table"],
                      "schema": e.get("schema"), "file": e["file"], "fields": len(e["fields"])}
                     for e in entities],
        "type_crosscheck": {"source": f"live target catalog (schema {sch})" if cols else reason,
                            "fields_checked": len(rows), "rows": rows},
    }


def render_md(r: dict, cap: int = 40) -> str:
    s, xc = r["sites"], r["type_crosscheck"]
    dialect = [x for x in s["sql"] if x["constructs"]]
    obl = [x for x in xc["rows"] if x.get("obligation") and not A.is_advisory(x["obligation"])]
    adv = [x for x in xc["rows"] if A.is_advisory(x.get("obligation"))]
    iss = [x for x in xc["rows"] if x.get("issue")]
    flagged = sorted({x["file"] for x in dialect} | {x["file"] for k in
                     ("routine", "error", "conn_code", "config") for x in s[k]} |
                     {x["file"] for x in obl + iss} | {x["file"] for x in s["resultset"]} |
                     {x["file"] for x in s["sql"] if not x["constructs"]})
    L = [f"# App scan — `{Path(r['app_dir']).name}` ({r['pair']})", "",
         "Deterministic pre-scan by `dbmig app-scan` (read-only). **Open only the flagged "  # nosemgrep: string-concat-in-list -- intentional: one long message split across lines
         "files**; full detail in `app-scan.yaml`.", "",
         f"- files in scope: **{r['files_in_scope']}** "  # nosemgrep: string-concat-in-list -- intentional: one long message split across lines
         f"({', '.join(f'{k} {v}' for k, v in list(r['files_by_type'].items())[:8])})",
         f"- frameworks detected: {', '.join(f'{k} ({len(v)} file(s))' for k, v in r['frameworks'].items()) or 'none'}",
         f"- excluded dirs: {', '.join(f'{k}×{v}' for k, v in r['excluded_dirs'].items()) or 'none'}",
         f"- leftovers (not conversion targets): {', '.join(r['leftovers']) or 'none'}",
         f"- **flagged files: {len(flagged)} of {r['files_in_scope']}**", "",
         "| Category | Sites | Files |", "|---|---|---|"]
    for label, items in (
            ("A. config (datasource/driver/dialect; plaintext secrets)", s["config"]),
            ("A. connection strings/URLs built in code", s["conn_code"]),
            ("B. embedded SQL with source-dialect constructs", dialect),
            ("B. other embedded SQL (no construct hit — still review for case/quoting)",
             [x for x in s["sql"] if not x["constructs"]]),
            ("C1. mapped fields with a REQUIRED type fix", obl),
            ("C1. type advisories (not blockers; review)", adv),
            ("C1. mapping issues (missing table/column, identifier case)", iss),
            ("D. stored-routine call sites", s["routine"]),
            ("E. error-code handling", s["error"]),
            ("F. result-set typing / column-name access", s["resultset"]),
            ("H. source-engine SQL scripts shipped with the app (flag; not converted unless in scope)",
             s["db_scripts"])):
        L.append(f"| {label} | {len(items)} | {len({x['file'] for x in items})} |")
    L += ["", f"Entities/models: {len(r['entities'])} "  # nosemgrep: string-concat-in-list -- intentional: one long message split across lines
          f"({', '.join(f'{k} {v}' for k, v in Counter(e['orm'] for e in r['entities']).items()) or 'none'}); "
          f"{xc['fields_checked']} mapped field(s) checked against **{xc['source']}**.", ""]

    def section(title, items, fmt):
        if not items:
            return
        L.extend([f"## {title}", ""] + [fmt(x) for x in items[:cap]])
        if len(items) > cap:
            L.append(f"- … {len(items) - cap} more in app-scan.yaml")
        L.append("")

    section("C1. Required type fixes (entity field ↔ migrated column)", obl,
            lambda x: f"- `{x['file']}:{x['line']}` {x['orm']} {x['entity']}.{x['field']} "
                      f"({x['type']}) → {x['table']}.{x['column']} [{x['target_type']}]: {x['obligation']}")
    section("C1. Type advisories (not blockers — review, change only if justified)", adv,
            lambda x: f"- `{x['file']}:{x['line']}` {x['entity']}.{x['field']} ({x['type']}) → "
                      f"{x['table']}.{x['column']} [{x['target_type']}]: {x['obligation'][len(A.ADVISORY):].strip()}")
    # issues: collapse identical per-table issues
    grouped: Dict[str, List[dict]] = {}
    for x in iss:
        grouped.setdefault(f"{x['orm']} {x['entity']} → {x['table']}: {x['issue'].split(':')[0]}", []).append(x)
    section("C1. Mapping issues", list(grouped.items()),
            lambda kv: f"- {kv[0]} — {len(kv[1])} field(s), e.g. `{kv[1][0]['file']}:{kv[1][0]['line']}` "
                       f"{kv[1][0]['field']}: {kv[1][0]['issue']}")
    section("B. Embedded SQL with source-dialect constructs", dialect,
            lambda x: f"- `{x['file']}:{x['line']}`{' **(Tier-3 fragment)**' if x.get('fragment') else ''}"
                      f" — {', '.join(x['constructs'])}: `{x['sql'][:140]}`")
    for title, key in (("D. Stored-routine call sites", "routine"), ("E. Error-code handling", "error"),
                       ("A. Connection strings/URLs built in code", "conn_code"),
                       ("A. Configuration", "config"), ("F. Result-set typing", "resultset")):
        section(title, s[key], lambda x: f"- `{x['file']}:{x['line']}`"
                f"{' **(' + x['kind'] + ')**' if x.get('kind') else ''} — `{x['text'][:140]}`")
    section("H. Source-engine SQL scripts", s["db_scripts"],
            lambda x: f"- `{x['file']}` ({x['bytes']} bytes) — {', '.join(x['constructs']) or 'no construct hits'}")
    L += ["## Flagged files (open these; the rest had no hits)", ""]
    L += [f"- `{f}`" for f in flagged[:200]]
    if len(flagged) > 200:
        L.append(f"- … {len(flagged) - 200} more in app-scan.yaml")
    L += ["", "Limits: static scanning cannot see SQL assembled from configuration/the "  # nosemgrep: string-concat-in-list -- intentional: one long message split across lines
          "database or generated by ORM criteria/LINQ; an ORM app with zero SQL text can "
          "still break (identifier case, types). The boot against the migrated target "
          "(Validation) is the proof."]
    return "\n".join(L) + "\n"


def run(args) -> int:
    app = Path(args.app_dir).expanduser().resolve()
    if not app.is_dir():
        console.err(f"application directory not found: {app}")
        return 2
    pair = config.active_pair()
    console.info(f"Scanning {app} ({pair}) ...")
    r = scan(app, pair, args.target_schema, check_target=not args.no_target)
    out = config.workspace_dir(args.project) / "05-application" / "01-assessment"
    out.mkdir(parents=True, exist_ok=True)
    (out / "app-scan.yaml").write_text(yaml.safe_dump(r, sort_keys=False, allow_unicode=True))
    (out / "app-scan.md").write_text(render_md(r))
    xc = r["type_crosscheck"]
    console.ok(f"{r['files_in_scope']} file(s); frameworks: {', '.join(r['frameworks']) or 'none'}; "
               f"dialect SQL sites: {sum(1 for x in r['sites']['sql'] if x['constructs'])}; "
               f"entities: {len(r['entities'])}; required type fixes: "
               f"{sum(1 for x in xc['rows'] if x.get('obligation') and not A.is_advisory(x['obligation']))}; "
               f"advisories: {sum(1 for x in xc['rows'] if A.is_advisory(x.get('obligation')))}; mapping issues: "
               f"{sum(1 for x in xc['rows'] if x.get('issue'))} ({xc['source']})")
    console.ok(f"Summary: {out / 'app-scan.md'}  (full: app-scan.yaml)")
    return 0
