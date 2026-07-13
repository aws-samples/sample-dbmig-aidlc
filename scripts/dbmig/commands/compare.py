"""``dbmig compare`` — reconcile source vs target (row counts) via adapters.

Counts rows per table on both engines and reports matches/mismatches. Failures
are handled per run-mode: silent (default) logs to follow-up and continues;
interactive surfaces via non-zero exit. Richer equivalence tests (function /
procedure parity) are driven by ``dbmig run-tests``.
"""
from __future__ import annotations

from typing import Dict, List, Optional

import yaml

from .. import config, console, engines, followup as fu
from ..connections import load_pair


def run(args) -> int:
    try:
        pair = load_pair()
        source = engines.get_source_engine(pair)
        target = engines.get_target_engine(pair)
    except config.ConfigError as exc:
        console.err(str(exc))
        return 2

    mode = fu.resolve_mode(args, config.load_migration_config())
    followup = fu.FollowUp(args.project)

    tables: Optional[List[str]] = None
    if getattr(args, "tables", None):
        tables = [t.strip() for t in args.tables.split(",") if t.strip()]

    failures = 0
    results: List[Dict] = []
    try:
        names = source.list_tables(args.schema, only=tables)
        if not names:
            console.warn("no tables to compare")
            return 0
        console.heading(f"Reconciliation — {len(names)} table(s)")
        for table in names:
            try:
                sc = source.count_rows(args.schema.upper(), table)
                tc = target.get_row_count(args.schema.lower(), table.lower())
            except Exception as exc:  # noqa: BLE001
                console.err(f"{table}: count failed: {exc}")
                results.append({"table": table, "status": "error",
                                "error": str(exc).strip()})
                failures += 1
                fu.handle_failure(mode, followup, phase="validation",
                                  kind="reconcile_error", obj=table,
                                  detail=str(exc).strip())
                continue
            status = "match" if sc == tc else "mismatch"
            if status == "mismatch":
                failures += 1
                console.err(f"{table}: source={sc:,} target={tc:,} MISMATCH")
                fu.handle_failure(mode, followup, phase="validation",
                                  kind="data_mismatch", obj=table,
                                  detail=f"source={sc} target={tc}")
            else:
                console.ok(f"{table}: {sc:,} rows match")
            results.append({"table": table, "source_rows": sc,
                            "target_rows": tc, "status": status})
    finally:
        source.close()
        target.close()

    outdir = config.workspace_dir(args.project) / "03-validation"
    outdir.mkdir(parents=True, exist_ok=True)
    report_path = outdir / config.manifest_file("reconcile_report", args.schema)
    report_path.write_text(
        yaml.safe_dump({"schema": args.schema.upper(), "mode": mode,
                        "results": results}, sort_keys=False))

    matches = sum(1 for r in results if r.get("status") == "match")
    console.heading("Reconciliation summary")
    console.ok(f"{matches}/{len(results)} table(s) match")
    if failures:
        console.warn(f"{failures} table(s) mismatch/error — recorded for follow-up "
                     f"({followup.open_count()} open); see {report_path}")
        if mode == fu.INTERACTIVE:
            return 1
        console.info("silent mode: continuing without blocking")
    return 0
