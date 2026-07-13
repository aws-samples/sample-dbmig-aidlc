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


def _run_function_case(src, tgt, case: Dict[str, Any], tol: float):
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

    results: List[Dict[str, Any]] = []
    passed = failed = skipped = 0
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
            for case in spec.get("cases", []) or []:
                cid = case.get("id", "?")
                try:
                    if otype == "procedure":
                        ok, detail = _run_procedure_case(src, tgt, case, tol)
                    else:
                        ok, detail = _run_function_case(src, tgt, case, tol)
                except Exception as exc:  # noqa: BLE001
                    src.rollback(); tgt.rollback()
                    ok, detail = False, {"error": str(exc).strip()}
                status = "pass" if ok else "fail"
                results.append({"object": obj, "type": otype, "case": cid,
                                "status": status, "detail": detail})
                if ok:
                    passed += 1
                    console.ok(f"{obj} [{cid}] pass")
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

    report = {
        "schema": args.schema.upper() if getattr(args, "schema", None) else manifest.get("schema"),
        "mode": mode,
        "summary": {"cases": len(results), "passed": passed, "failed": failed,
                    "skipped": skipped},
        "results": results,
    }
    ws.mkdir(parents=True, exist_ok=True)
    report_path = ws / config.manifest_file("equivalence-report", args.schema)
    report_path.write_text(yaml.safe_dump(report, sort_keys=False))
    _write_md(report_path.with_suffix(".md"), report)

    console.heading("Equivalence test results")
    console.ok(f"passed {passed}/{len(results)} (skipped {skipped} ungenerated)")
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
        f"Mode: `{report.get('mode')}`  |  Cases: {s['cases']}  "
        f"Passed: {s['passed']}  Failed: {s['failed']}  Skipped: {s['skipped']}",
        "",
        "| Object | Type | Case | Status | Detail |",
        "|---|---|---|---|---|",
    ]
    for r in report["results"]:
        d = str(r["detail"]).replace("\n", " ").replace("|", "\\|")
        if len(d) > 160:
            d = d[:160] + "…"
        lines.append(f"| {r['object']} | {r['type']} | {r['case']} | "
                     f"{r['status']} | {d} |")
    path.write_text("\n".join(lines) + "\n")
