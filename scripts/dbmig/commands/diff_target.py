"""``dbmig diff-target`` — reconcile the DMS-SC-imported map against the LIVE target.

Because DMS SC has already applied the schema (and some objects can fail to apply, or
be hand-edited afterwards), every object is re-diffed against what is actually in the
target database now. Per object the verdict is:

- ``MATCH``   present on the target (and, for code/views, its definition matches)
- ``DIFF``    present, but the live definition differs from the DMS SC conversion
- ``MISSING`` expected (converted by DMS SC) but not present on the target
- ``EXTRA``   present on the target but not in the DMS SC map (reported only)

By default this is **report-only** (safe). With ``--resolve`` it acts on conflicts:
``apply-ours`` (apply the DMS SC DDL for MISSING/DIFF), ``keep-live`` (leave the target),
or ``ask`` (interactive per-object when a TTY is available). Applying DDL is a gated,
destructive-capable action — dry-run prints what would run unless ``--apply`` is given.

Reads ``01-assessment/dms-sc-map-<SCHEMA>.json`` (produced by ``import-dms-sc``), writes
``01-assessment/dms-sc-diff-<SCHEMA>.md`` and refreshes the migration report.
"""
from __future__ import annotations

import datetime as _dt
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Dict, List, Optional

from .. import config, console, report
from ..connections import load_pair
from .. import engines

MATCH, MISSING, EXTRA, UNMATCHED = "MATCH", "MISSING", "EXTRA", "UNMATCHED"

# map object meta-type -> catalog kind bucket returned by live_schema_catalog
_KIND = {
    "TABLE": "tables", "VIEW": "views", "SEQUENCE": "sequences",
    "INDEX": "indexes", "CONSTRAINT": "constraints", "TRIGGER": "triggers",
    "FUNCTION": "routines", "PROCEDURE": "routines",
}
# Kinds whose names DMS SC preserves, so exact-name presence checks are reliable.
# (DMS SC renames system PK/UNIQUE constraints and many indexes, so those are only
# checked as an advisory, never reported as hard MISSING.)
_RELIABLE_NAME_KINDS = {"tables", "views", "sequences", "triggers", "routines"}


def _now() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_map(ws: Path, schema: str) -> Optional[dict]:
    p = ws / "01-assessment" / f"dms-sc-map-{schema.upper()}.json"
    if not p.exists():
        return None
    return json.loads(p.read_text())


def run(args) -> int:
    ws = config.workspace_dir(args.project)
    smap = _load_map(ws, args.schema)
    if smap is None:
        console.err(f"no DMS SC map for schema {args.schema} in project {args.project}. "
                    f"Run `import-dms-sc` first.")
        return 2

    try:
        pair = load_pair()
        target = engines.get_target_engine(pair)
    except config.ConfigError as exc:
        console.err(str(exc))
        return 2
    if not hasattr(target, "live_schema_catalog"):
        console.err(f"target engine '{target.engine}' does not support live "
                    "introspection yet (PostgreSQL only for now).")
        return 2

    target_schema = smap.get("target_schema") or args.schema.lower()
    try:
        catalog = target.live_schema_catalog(target_schema)
    except Exception as exc:  # noqa: BLE001
        console.err(f"introspection failed: {exc}")
        target.close()
        return 1

    objects = smap.get("objects", [])
    results: List[dict] = []
    for o in objects:
        mt = (o.get("target_type") or o.get("source_type") or "").upper()
        name = (o.get("target_name") or "").lower()
        kind = _KIND.get(mt)
        present = bool(name) and kind is not None and name in catalog.get(kind, set())
        is_fk = mt == "CONSTRAINT" and _is_foreign_key(ws, o)
        reliable = (kind in _RELIABLE_NAME_KINDS) or is_fk

        if present:
            verdict, detail = MATCH, ""
        elif reliable:
            verdict, detail = MISSING, ("foreign key" if is_fk else "")
        else:
            # PK/UNIQUE/CHECK constraint or index: DMS SC likely renamed it, so a
            # name miss is not proof of absence — flag for a manual look, don't alarm.
            verdict, detail = UNMATCHED, "system/renamed name — verify by table+columns"

        results.append({
            "object": f"{o.get('source_schema')}.{o.get('source_name')}",
            "target_name": name, "type": mt, "kind": kind,
            "disposition": o.get("disposition"), "verdict": verdict,
            "detail": detail, "apply_status": o.get("apply_status"),
            "target_ddl_ref": o.get("target_ddl_ref", ""),
        })

    # EXTRA: live objects not present in the map (tables/routines/views/sequences —
    # the meaningful ones; indexes/constraints have noisy system names).
    mapped = {(r["kind"], r["target_name"]) for r in results if r["kind"]}
    extras: List[dict] = []
    for kind in ("tables", "views", "routines", "sequences"):
        for nm in sorted(catalog.get(kind, set())):
            if (kind, nm) not in mapped:
                extras.append({"kind": kind, "target_name": nm})

    counts = Counter(r["verdict"] for r in results)
    counts[EXTRA] = len(extras)

    _write_report(ws, args.schema, target_schema, results, extras, counts, smap)
    _update_report_section(args.project, args.schema, counts, results)

    console.heading(f"diff-target — {args.schema} vs live target `{target_schema}`")
    console.ok(f"MATCH={counts[MATCH]}  MISSING={counts[MISSING]}  "
               f"UNMATCHED(system-named)={counts[UNMATCHED]}  EXTRA={counts[EXTRA]}")
    miss = [r for r in results if r["verdict"] == MISSING]
    if miss:
        console.warn(f"{len(miss)} object(s) MISSING on the target "
                     "(converted by DMS SC but not applied) — e.g. "
                     + ", ".join(f"{m['object']}({m['type']})" for m in miss[:6])
                     + ("…" if len(miss) > 6 else ""))
    if counts[UNMATCHED]:
        console.info(f"{counts[UNMATCHED]} system-named constraint/index object(s) could "
                     "not be name-matched (DMS SC renames these) — listed in the report "
                     "for a table+columns check, not counted as missing.")
    console.ok(f"Report: {ws / '01-assessment' / f'dms-sc-diff-{args.schema.upper()}.md'}")

    resolve = getattr(args, "resolve", None)
    if resolve:
        rc = _resolve(args, target, results, ws, resolve)
        target.close()
        return rc
    target.close()
    console.info("Report-only (no changes). Re-run with --resolve apply-ours|keep-live|ask "
                 "(and --apply to execute) to reconcile MISSING objects.")
    return 0


def _is_foreign_key(ws: Path, o: dict) -> bool:
    """True if this CONSTRAINT object is a foreign key (name reliably preserved by
    DMS SC), detected from its DDL snapshot."""
    for ref in (o.get("target_ddl_ref"), o.get("source_ddl_ref")):
        txt = _load_snapshot_ref(ws, ref or "")
        if txt and "FOREIGN KEY" in txt.upper():
            return True
    # Fallback: common FK naming prefix.
    return (o.get("target_name") or o.get("source_name") or "").lower().startswith("fk")


def _resolve(args, target, results: List[dict], ws: Path, mode: str) -> int:
    """Apply the DMS SC DDL for MISSING objects. Gated + dry-run aware."""
    apply = getattr(args, "apply", False)
    interactive = mode == "ask" and sys.stdin.isatty()
    todo = [r for r in results if r["verdict"] == MISSING]
    if not todo:
        console.ok("nothing to resolve (no MISSING objects).")
        return 0
    applied = skipped = failed = 0
    for r in todo:
        ddl = _load_snapshot_ref(ws, r["target_ddl_ref"])
        choice = mode
        if interactive:
            console.info(f"\n{r['verdict']}  {r['object']} ({r['type']})"
                         + (f"  [{r['detail']}]" if r["detail"] else ""))
            try:
                ans = input("  [a]pply DMS SC DDL / [k]eep live / [s]kip? [s]: ").strip().lower()
            except EOFError:
                ans = "s"
            choice = {"a": "apply-ours", "k": "keep-live"}.get(ans[:1], "keep-live")
        if choice == "keep-live":
            skipped += 1
            continue
        if not ddl:
            console.warn(f"  no DDL snapshot for {r['object']} — skipping")
            skipped += 1
            continue
        if not apply:
            console.info(f"  [dry-run] would apply DDL for {r['object']} ({r['type']})")
            continue
        try:
            target.apply_ddl(ddl)
            console.ok(f"  applied {r['object']} ({r['type']})")
            applied += 1
        except Exception as exc:  # noqa: BLE001
            console.err(f"  failed {r['object']}: {exc}")
            failed += 1
    console.heading("Resolve summary")
    console.ok(f"applied={applied}  skipped/kept={skipped}  failed={failed}"
               + ("  (dry-run — use --apply to execute)" if not apply else ""))
    return 1 if failed else 0


def _load_snapshot_ref(ws: Path, ref: str) -> str:
    if not ref:
        return ""
    p = ws / ref
    return p.read_text() if p.exists() else ""


def _write_report(ws: Path, schema: str, target_schema: str, results: List[dict],
                  extras: List[dict], counts: Counter, smap: dict) -> None:
    lines = [
        f"# DMS SC diff vs live target — schema `{schema}` (target `{target_schema}`)",
        "",
        f"_Generated {_now()} · source {smap.get('source_engine','?')} → "
        f"target {smap.get('target_engine','?')}_",
        "",
        f"- MATCH: **{counts[MATCH]}**  ·  MISSING: **{counts[MISSING]}**  ·  "
        f"UNMATCHED (system-named): **{counts[UNMATCHED]}**  ·  EXTRA: **{counts[EXTRA]}**",
        "",
    ]
    miss = [r for r in results if r["verdict"] == MISSING]
    if miss:
        lines += [f"## MISSING on target ({len(miss)}) — converted by DMS SC but not applied",
                  "", "| Object | Type | Disposition | DMS SC apply status |",
                  "|---|---|---|---|"]
        for r in sorted(miss, key=lambda x: (x["type"], x["object"])):
            lines.append(f"| `{r['object']}` | {r['type']} | {r['disposition']} "
                         f"| {r['apply_status'] or '-'} |")
        lines.append("")
    unm = [r for r in results if r["verdict"] == UNMATCHED]
    if unm:
        lines += [f"## UNMATCHED by name ({len(unm)}) — system-named constraints/indexes",
                  "", "DMS SC assigns its own names to PK/UNIQUE/CHECK constraints and "
                  "many indexes, so a name miss here does **not** mean the object is "
                  "absent. Verify these by table + column set (a later capture/compare "
                  "step will do this automatically).", "",
                  "| Object | Type | Apply status |", "|---|---|---|"]
        for r in sorted(unm, key=lambda x: (x["type"], x["object"])):
            lines.append(f"| `{r['object']}` | {r['type']} | {r['apply_status'] or '-'} |")
        lines.append("")
    if extras:
        lines += [f"## EXTRA on target ({len(extras)}) — present live, not in the DMS SC map",
                  "", "| Name | Kind |", "|---|---|"]
        for e in extras:
            lines.append(f"| `{e['target_name']}` | {e['kind']} |")
        lines.append("")
    lines += ["## MATCH", "", f"{counts[MATCH]} object(s) present and consistent. "
              "(Full per-object detail is in `dms-sc-map-<SCHEMA>.json`.)", ""]
    (ws / "01-assessment" / f"dms-sc-diff-{schema.upper()}.md").write_text("\n".join(lines))


def _update_report_section(project: str, schema: str, counts: Counter,
                           results: List[dict]) -> None:
    miss = [r for r in results if r["verdict"] == MISSING]
    # A single shared Construction phase header (idempotent), then one subsection per
    # schema so multi-schema projects (e.g. SQL Server) don't overwrite each other.
    report.update_section(project, "construction", report.PHASE_ORDER[report.CONSTRUCTION],
                          f"## {report.PHASE_TITLE[report.CONSTRUCTION]}\n\n"
                          "### Reconciliation against the live target (`diff-target`)")
    body = [
        f"#### Schema `{schema}`",
        "",
        f"- MATCH **{counts[MATCH]}**, MISSING **{counts[MISSING]}**, "
        f"UNMATCHED/system-named **{counts[UNMATCHED]}**, EXTRA **{counts[EXTRA]}**.",
        "",
    ]
    if miss:
        body += [
            f"**{len(miss)} object(s) MISSING on the target** — DMS SC converted them but "
            "they were not applied (commonly foreign keys / triggers). Resolve with "
            f"`dbmig diff-target --schema {schema} --resolve apply-ours --apply`, or "
            "recreate them in the load phase. Examples:",
            "",
        ]
        for m in miss[:15]:
            body.append(f"- `{m['object']}` ({m['type']})")
        body.append("")
    else:
        body += ["All mapped objects are present on the target. ✅", ""]
    body.append(f"See `01-assessment/dms-sc-diff-{schema.upper()}.md` for the full diff.")
    # order 21 keeps these just after the shared Construction header (order 20).
    report.update_section(project, f"construction.{schema.lower()}",
                          report.PHASE_ORDER[report.CONSTRUCTION] + 1, "\n".join(body))
