"""``dbmig run-tests`` — execute equivalence tests on source vs target.

Reads the ``.test.yaml`` specs Kiro generated (from ``gen-tests``) and runs each
case on BOTH engines **inside a transaction that is rolled back** afterward — so
the tests are representative (they use real data and exercise real writes) yet
non-destructive.

- **Functions**: run the call on each engine, compare the return value.
- **Procedures**: snapshot each verify-probe BEFORE and AFTER the call on each
  engine, then compare the delta (after - before) across source and target —
  i.e. the *net effect* matches.

Any comparison failure is handled per run-mode: ``silent`` (default) records it to
the follow-up log and continues; ``interactive`` also prompts. Writes
``03-validation/equivalence-report.yaml`` and ``.md``.
"""
from __future__ import annotations

import numbers
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from .. import config, console, engines, followup as fu
from ..connections import load_pair

# Data-coverage level (set per unit by gen-tests) meaning every table the object
# reads was empty in the source.
LOW_COVERAGE = "LOW_COVERAGE"


# ---- execution helpers (operate on engine adapters: scalar/execute/rollback) ----

def _scalar(eng, sql: str):
    return eng.scalar(sql)


def _stmt(eng, sql: str) -> None:
    eng.execute(sql)


def _equal(a, b, tol: float, norm_ws: bool = True) -> bool:
    if a is None or b is None:
        return a is None and b is None
    if isinstance(a, numbers.Number) and isinstance(b, numbers.Number):
        try:
            return abs(float(a) - float(b)) <= tol
        except (TypeError, ValueError):
            return a == b
    sa, sb = str(a), str(b)
    if norm_ws:
        sa, sb = " ".join(sa.split()), " ".join(sb.split())
    return sa == sb


def _delta(before, after):
    """Net-effect descriptor for a probe, comparable across engines.

    Numeric probes -> the signed delta ``after - before`` (compared with tolerance).
    Non-numeric probes -> a transition descriptor ``(changed, after)`` capturing WHAT
    the call did — whether the probed value changed, and its resulting value — WITHOUT
    requiring the pre-call snapshots to match across engines. Absolute before/after
    values legitimately differ (auto-increment seeds, timestamps, an incompletely
    reset prior case), so the old ``(before, after)`` tuple compared with ``==``
    produced spurious FAILs (differing seeds) and false PASSes (matching absolutes).
    This restores the "compare the delta" contract for the non-numeric path.
    """
    if isinstance(before, numbers.Number) and isinstance(after, numbers.Number):
        return float(after) - float(before)
    return (not _equal(before, after, 0.0), after)


def _delta_equal(sd, td, tol: float) -> bool:
    """Compare two net-effect descriptors from ``_delta`` (numeric or transition).

    For the transition form ``(changed, after)``: the engines must agree on whether
    the probe changed; if neither changed, the net effect is "no change" on both and
    they match regardless of the (pre-existing, possibly seed-dependent) absolute
    value — mirroring the numeric case where ``0.0 == 0.0`` irrespective of the base.
    If both changed, the resulting values are compared.
    """
    if isinstance(sd, tuple) or isinstance(td, tuple):
        if not (isinstance(sd, tuple) and isinstance(td, tuple)):
            return False
        (s_changed, s_after), (t_changed, t_after) = sd, td
        if s_changed != t_changed:
            return False
        if not s_changed:
            return True
        return _equal(s_after, t_after, tol)
    return _equal(sd, td, tol)


def _rows(eng, sql: str) -> List[tuple]:
    """All rows of a query (or of the first result set of a CALL, e.g. a MySQL procedure
    that replaced a set-returning function)."""
    _cols, rows = eng.fetch(sql)
    return [tuple(r) for r in rows]


def _row_key(row: tuple) -> tuple:
    """Engine-neutral sort key: numbers by value, everything else by its string form."""
    return tuple((0, float(v), "") if isinstance(v, numbers.Number) else
                 (1, 0.0, "" if v is None else " ".join(str(v).split())) for v in row)


def _resultset_equal(srows: List[tuple], trows: List[tuple], tol: float,
                     ordered: bool) -> bool:
    if len(srows) != len(trows):
        return False
    if not ordered:
        srows, trows = sorted(srows, key=_row_key), sorted(trows, key=_row_key)
    for sr, tr in zip(srows, trows):
        if len(sr) != len(tr) or not all(_equal(a, b, tol) for a, b in zip(sr, tr)):
            return False
    return True


def _run_function_case(src, tgt, case: Dict[str, Any], tol: float):
    if str(case.get("compare") or "scalar").strip().lower() == "resultset":
        # Compare every row and column, not just the first value. Rows are sorted
        # before comparing unless the case says `ordered: true` (ORDER BY ties and
        # engine plan differences make row order unreliable otherwise).
        s_rows = _rows(src, case["source_sql"])
        t_rows = _rows(tgt, case["target_sql"])
        src.rollback()
        tgt.rollback()
        ok = _resultset_equal(s_rows, t_rows, tol, bool(case.get("ordered")))
        return ok, {"source_rows": len(s_rows), "target_rows": len(t_rows),
                    "source_first": _str(s_rows[0]) if s_rows else None,
                    "target_first": _str(t_rows[0]) if t_rows else None}
    s = _scalar(src, case["source_sql"])
    t = _scalar(tgt, case["target_sql"])
    src.rollback()
    tgt.rollback()
    ok = _equal(s, t, tol)
    return ok, {"source": _str(s), "target": _str(t)}


def _run_procedure_case(src, tgt, case: Dict[str, Any], tol: float):
    probes = case.get("verify", []) or []
    s_before = {p["name"]: _scalar(src, p["source_sql"]) for p in probes}
    _stmt(src, case["call_source"])
    s_after = {p["name"]: _scalar(src, p["source_sql"]) for p in probes}

    t_before = {p["name"]: _scalar(tgt, p["target_sql"]) for p in probes}
    _stmt(tgt, case["call_target"])
    t_after = {p["name"]: _scalar(tgt, p["target_sql"]) for p in probes}

    src.rollback()
    tgt.rollback()

    detail = {}
    ok = True
    for p in probes:
        name = p["name"]
        sd = _delta(s_before[name], s_after[name])
        td = _delta(t_before[name], t_after[name])
        match = _delta_equal(sd, td, tol)
        ok = ok and match
        detail[name] = {"source_delta": _str(sd), "target_delta": _str(td),
                        "match": match}
    return ok, detail


def _str(v):
    return None if v is None else str(v)


def run(args) -> int:
    try:
        pair = load_pair()
    except config.ConfigError as exc:
        console.err(str(exc))
        return 2
    if "source" not in pair or "target" not in pair:
        console.err("run-tests requires both 'source' and 'target' connections")
        return 2

    mig = config.load_migration_config()
    mode = fu.resolve_mode(args, mig)
    followup = fu.FollowUp(args.project)
    eq = (mig.get("testing") or {}).get("equivalence") or {}
    tol = float(eq.get("float_tolerance", 1e-9))

    ws = config.workspace_dir(args.project) / "03-validation"
    manifest_path = config.resolve_manifest(ws, "test-manifest", args.schema)
    if not manifest_path.exists():
        console.err(f"test manifest not found: {manifest_path} (run gen-tests first)")
        return 2
    manifest = yaml.safe_load(manifest_path.read_text()) or {}
    units = manifest.get("units", [])

    # Build adapters once; each case rolls back so connections stay clean.
    try:
        src = engines.get_source_engine(pair)
        tgt = engines.get_target_engine(pair)
    except config.ConfigError as exc:
        console.err(str(exc))
        return 2

    # The source login is often NOT the schema owner (e.g. Oracle 'admin' vs
    # 'DEMO'), so unqualified probe SQL would fail (ORA-00942). Point the source
    # session at the schema under test; a no-op for engines without the concept.
    schema_name = args.schema or manifest.get("schema")
    if schema_name:
        try:
            src.set_session_schema(schema_name)
        except Exception as exc:  # noqa: BLE001
            console.warn(f"could not set source session schema to {schema_name}: "
                         f"{exc} — qualify source probe SQL with the schema")

    results: List[Dict[str, Any]] = []
    passed = failed = skipped = 0
    passed_keys: List[str] = []
    low_coverage: List[str] = []
    aborted = False
    try:
        for u in units:
            spec_path = ws / u["spec_file"]
            if not spec_path.exists():
                skipped += 1
                continue
            try:
                spec = yaml.safe_load(spec_path.read_text()) or {}
            except Exception as exc:  # noqa: BLE001
                console.err(f"{u['name']}: invalid test spec: {exc}")
                skipped += 1
                continue
            obj = f"{spec.get('schema', u.get('schema'))}.{spec.get('object', u.get('name'))}"
            otype = (spec.get("type") or "function").strip().lower()
            coverage = ((u.get("data_coverage") or {}).get("level")) or "n/a"
            if coverage == LOW_COVERAGE and obj not in low_coverage:
                low_coverage.append(obj)
            for case in spec.get("cases", []) or []:
                cid = case.get("id", "?")
                # A case may override the spec type — packages mix functions and
                # procedures, so one package spec can hold both kinds of case.
                ctype = (case.get("type") or otype).strip().lower()
                try:
                    if ctype == "procedure":
                        ok, detail = _run_procedure_case(src, tgt, case, tol)
                    else:
                        ok, detail = _run_function_case(src, tgt, case, tol)
                except Exception as exc:  # noqa: BLE001
                    src.rollback(); tgt.rollback()
                    ok, detail = False, {"error": str(exc).strip()}
                status = "pass" if ok else "fail"
                results.append({"object": obj, "type": ctype, "case": cid,
                                "status": status, "coverage": coverage,
                                "detail": detail})
                if ok:
                    passed += 1
                    passed_keys.append(f"{obj} [{cid}]")
                    console.item_ok(f"{obj} [{cid}] pass")
                else:
                    failed += 1
                    console.err(f"{obj} [{cid}] FAIL: {detail}")
                    action = fu.handle_failure(
                        mode, followup, phase="validation", kind="test_failure",
                        obj=f"{obj} [{cid}]", detail=str(detail))
                    if action == "abort":
                        aborted = True
                        break
            if aborted:
                break
    finally:
        src.close()
        tgt.close()

    console.flush_items("03-validation/equivalence-report-<SCHEMA>.md")
    # A case that failed on an earlier run and passes now closes its ledger item.
    resolved = followup.resolve("test_failure", passed_keys,
                                note="passed on run-tests re-run")

    report = {
        "schema": args.schema.upper() if getattr(args, "schema", None) else manifest.get("schema"),
        "mode": mode,
        "summary": {"cases": len(results), "passed": passed, "failed": failed,
                    "skipped": skipped, "low_coverage_objects": len(low_coverage)},
        "low_coverage": low_coverage,
        "results": results,
    }
    ws.mkdir(parents=True, exist_ok=True)
    report_path = ws / config.manifest_file("equivalence-report", args.schema)
    report_path.write_text(yaml.safe_dump(report, sort_keys=False))
    _write_md(report_path.with_suffix(".md"), report)

    console.heading("Equivalence test results")
    console.ok(f"passed {passed}/{len(results)} (skipped {skipped} ungenerated)")
    if resolved:
        console.ok(f"{resolved} previously-failed follow-up item(s) auto-resolved")
    if low_coverage:
        console.warn(f"{len(low_coverage)} object(s) are {LOW_COVERAGE} (every table "
                     "they read was empty in the source — only the empty/default path "
                     "was exercised): " + ", ".join(low_coverage))
    if failed:
        console.warn(f"{failed} case(s) failed — recorded to {followup.path.name} "
                     f"({followup.open_count()} open follow-up item(s))")
    # Silent mode never blocks the run; interactive surfaces failures.
    if mode == fu.INTERACTIVE and (failed or aborted):
        return 1
    return 0


def _write_md(path: Path, report: Dict[str, Any]) -> None:
    s = report["summary"]
    lines = [
        f"# Equivalence Test Report — {report.get('schema')}",
        "",
        f"Mode: `{report.get('mode')}`  |  Cases: {s['cases']}  "  # nosemgrep: string-concat-in-list -- intentional: one long message split across lines
        f"Passed: {s['passed']}  Failed: {s['failed']}  Skipped: {s['skipped']}",
        "",
    ]
    if report.get("low_coverage"):
        lines += [
            f"**{LOW_COVERAGE}** — every table these objects read was empty in the "  # nosemgrep: string-concat-in-list -- intentional: one long message split across lines
            "source, so the tests exercised only the empty / default path. A pass here "
            "is honest but shallow; re-test with representative data before cutover:",
            "",
            *[f"- `{o}`" for o in report["low_coverage"]],
            "",
        ]
    lines += [
        "| Object | Type | Case | Status | Coverage | Detail |",
        "|---|---|---|---|---|---|",
    ]
    for r in report["results"]:
        d = str(r["detail"]).replace("\n", " ").replace("|", "\\|")
        if len(d) > 160:
            d = d[:160] + "…"
        lines.append(f"| {r['object']} | {r['type']} | {r['case']} | "
                     f"{r['status']} | {r.get('coverage', 'n/a')} | {d} |")
    path.write_text("\n".join(lines) + "\n")
