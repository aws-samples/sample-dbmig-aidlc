"""``dbmig reset-identity`` — sync identity/serial/AUTO_INCREMENT counters on the
target to the data actually loaded, and PROVE it.

After a data load (``migrate-data``, AWS DMS, or a final cutover sync) the rows
carry explicit keys, but the target's identity sequences still sit at their
start value — so the application's first INSERT collides with a migrated row.

This command reads the target catalog (it does not guess from a template), so it
touches exactly the tables that really have an identity-backed column and skips
the ones that do not. For each identity column it reports ``MAX(key)`` and the
next value the target would generate; with ``--apply`` it syncs the counter so
the next value is ``MAX(key)+1`` (or the sequence START when the table is empty)
and re-reads the catalog to verify ``next_value > max_id``.

It also lists **standalone sequences** (not owned by any column) on both sides:
those are not covered by an identity reset and must be set to the source value
at cutover.

Default is a dry run (report only). Writes
``04-operations/identity-reset-<SCHEMA>.yaml`` + ``.md`` — the ``.md`` is the
cutover-runbook step, generated from the real catalog.
"""
from __future__ import annotations

import datetime as _dt
from typing import Any, Dict, List, Optional

import yaml

from .. import config, console, engines
from ..connections import load_pair

OK = "OK"
NEEDS_SYNC = "NEEDS_SYNC"
UNKNOWN = "UNKNOWN"


def verdict(max_id: Optional[int], next_value: Optional[int]) -> str:
    """OK when the next generated key cannot collide with a loaded row."""
    if next_value is None:
        return UNKNOWN
    if max_id is None:
        return OK
    return OK if next_value > max_id else NEEDS_SYNC


def _now() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def run(args) -> int:
    try:
        pair = load_pair()
    except config.ConfigError as exc:
        console.err(str(exc))
        return 2
    if "target" not in pair:
        console.err("reset-identity requires a 'target' connection")
        return 2

    tgt_schema = (getattr(args, "target_schema", None) or args.schema).lower()
    only = None
    if getattr(args, "tables", None):
        only = {t.strip().lower() for t in args.tables.split(",") if t.strip()}

    try:
        target = engines.get_target_engine(pair)
    except config.ConfigError as exc:
        console.err(str(exc))
        return 2

    rows: List[Dict[str, Any]] = []
    target_seqs: List[Dict[str, Any]] = []
    try:
        cols = target.identity_columns(tgt_schema)
        if only:
            cols = [c for c in cols if c["table"].lower() in only]
        for c in cols:
            before = target.identity_state(tgt_schema, c["table"], c["column"],
                                           c["sequence"])
            row = {"table": c["table"], "column": c["column"],
                   "sequence": c["sequence"], "max_id": before["max_id"],
                   "next_before": before["next_value"],
                   "status_before": verdict(before["max_id"], before["next_value"])}
            if args.apply:
                target.sync_identity(tgt_schema, c["table"], c["column"], c["sequence"])
                after = target.identity_state(tgt_schema, c["table"], c["column"],
                                              c["sequence"])
                row["max_id"] = after["max_id"]
                row["next_after"] = after["next_value"]
                row["status"] = verdict(after["max_id"], after["next_value"])
            else:
                row["status"] = row["status_before"]
            rows.append(row)
        target_seqs = target.standalone_sequences(tgt_schema)
    finally:
        target.close()

    # Standalone sequences on the source (optional — source may be unreachable
    # at cutover time; this is informational).
    source_seqs: List[Dict[str, Any]] = []
    if "source" in pair:
        try:
            source = engines.get_source_engine(pair)
            try:
                source_seqs = source.standalone_sequences(args.schema)
            finally:
                source.close()
        except Exception as exc:  # noqa: BLE001
            console.warn(f"could not read source sequences: {exc}")

    report = {
        "schema": args.schema.upper(),
        "target_schema": tgt_schema,
        "generated_at": _now(),
        "applied": bool(args.apply),
        "identity_columns": rows,
        "standalone_sequences": {"source": source_seqs, "target": target_seqs},
        "summary": {
            "identity_columns": len(rows),
            "ok": sum(1 for r in rows if r["status"] == OK),
            "needs_sync": sum(1 for r in rows if r["status"] == NEEDS_SYNC),
            "unknown": sum(1 for r in rows if r["status"] == UNKNOWN),
        },
    }
    ws = config.workspace_dir(args.project) / "04-operations"
    ws.mkdir(parents=True, exist_ok=True)
    yml = ws / f"identity-reset-{args.schema.upper()}.yaml"
    yml.write_text(yaml.safe_dump(report, sort_keys=False))
    md = yml.with_suffix(".md")
    md.write_text(render_md(report, args.project))

    console.heading(f"Identity reset — {tgt_schema} "
                    f"({'APPLIED' if args.apply else 'dry run'})")
    for r in rows:
        nxt = r.get("next_after", r["next_before"])
        line = (f"{r['table']}.{r['column']}: max={r['max_id']} next={nxt} "
                f"[{r['status']}]")
        (console.item_ok if r["status"] == OK else console.warn)(line)
    console.flush_items(str(md))
    if not rows:
        console.info("no identity/serial/AUTO_INCREMENT columns found")
    s = report["summary"]
    console.ok(f"{s['ok']}/{s['identity_columns']} identity column(s) safe")
    if target_seqs or source_seqs:
        console.warn(f"standalone sequences (NOT covered — sync to the source value "
                     f"at cutover): source={len(source_seqs)} target={len(target_seqs)}")
    console.ok(f"Report + runbook step: {md}")
    if s["needs_sync"] and not args.apply:
        console.info("re-run with --apply to sync the counters (writes to the target)")
    # After --apply every column must verify; a dry run just reports.
    if args.apply and (s["needs_sync"] or s["unknown"]):
        return 1
    return 0


def render_md(report: Dict[str, Any], project: str) -> str:
    s = report["summary"]
    rows = report["identity_columns"]
    applied = report["applied"]
    lines = [
        "> ⚠️ **AI-GENERATED — review before use.** Generated by `dbmig reset-identity` "  # nosemgrep: string-concat-in-list -- intentional: one long message split across lines
        "from the live target catalog; validate in a non-production environment first.",
        "",
        f"# Identity / sequence reset — `{report['schema']}` → `{report['target_schema']}`",
        "",
        f"Generated {report['generated_at']} — "  # nosemgrep: string-concat-in-list -- intentional: one long message split across lines
        f"{'**applied** and re-verified' if applied else 'dry run (nothing changed)'}. "
        f"{s['ok']}/{s['identity_columns']} identity column(s) safe"
        f"{', ' + str(s['needs_sync']) + ' need sync' if s['needs_sync'] else ''}.",
        "",
        "## Runbook step — run AFTER the final data sync, BEFORE opening app traffic",
        "",
        "```bash",
        f"./dbmig reset-identity --schema {report['schema']} "  # nosemgrep: string-concat-in-list -- intentional: one long message split across lines
        f"--target-schema {report['target_schema']} --project {project} --apply",
        "```",
        "",
        f"Scope: exactly the {len(rows)} table(s) below with an identity-backed column "  # nosemgrep: string-concat-in-list -- intentional: one long message split across lines
        "(read from the catalog). Tables without one are not touched. The command "
        "exits non-zero if any column fails verification (`next_value > max_id`).",
        "",
        "| Table | Column | Sequence | MAX(id) | Next (before) | Next (after) | Status |",
        "|---|---|---|---|---|---|---|",
    ]
    for r in rows:
        lines.append(
            f"| {r['table']} | {r['column']} | {r.get('sequence') or '—'} | "
            f"{'—' if r['max_id'] is None else r['max_id']} | "
            f"{'—' if r['next_before'] is None else r['next_before']} | "
            f"{'—' if r.get('next_after') is None else r['next_after']} | "
            f"{r['status']} |")
    ss = report["standalone_sequences"]
    lines += ["", "## Standalone sequences (not covered by the identity reset)", ""]
    if not ss["source"] and not ss["target"]:
        lines.append("None on either side — every sequence backs an identity column.")
    else:
        lines.append("Set each target sequence to its source value at cutover "
                     "(after the source is frozen):")
        lines.append("")
        lines.append("| Side | Sequence | Last value |")
        lines.append("|---|---|---|")
        for side in ("source", "target"):
            for q in ss[side]:
                lines.append(f"| {side} | {q['name']} | {q.get('last_value')} |")
    lines += [
        "",
        "## Manual verification query",
        "",
        "Re-run the command without `--apply` — every row must show `OK`.",
        "",
    ]
    return "\n".join(lines) + "\n"
