"""``dbmig import-dms-sc`` — ingest an existing AWS DMS Schema Conversion project.

Reads a **local DMS SC project directory** (no database access) and, for every schema it
finds, produces the dbmig artifacts that let the normal pipeline continue:

- ``01-assessment/dms-sc-map-<SCHEMA>.json`` — full leaf-granular mapping + classification
  (the source of truth later phases consume; keyed on source node id).
- ``01-assessment/dms-sc-classification-<SCHEMA>.md`` — human triage report.
- ``01-assessment/dms-sc/<SCHEMA>/{source,target}/*.sql`` — DDL snapshots.
- ``02-construction/code-manifest-<SCHEMA>.yaml`` (+ ``code/<tschema>/*.sql``) — code
  objects, pre-populated with the DMS-SC-converted DDL, ready for the existing
  apply/convert/test commands.

Each object is classified **ACCEPT** (keep DMS SC output), **VERIFY** (keep, but prove
with equivalence tests) or **MANUAL** (must be reconverted). See
``docs/dms-sc-import-design.md``.
"""
from __future__ import annotations

import datetime as _dt
import hashlib
import json
import re
from collections import Counter
from pathlib import Path
from typing import Dict, List

import yaml

from .. import config, console, report
from ..manifest import write_manifest
from ..dmssc import parse_project, classify
from ..dmssc.classify import ACCEPT, VERIFY, MANUAL
from ..dmssc.parser import load_apply_results
from ..dmssc.model import DmsScObject, ImportResult


def _now() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _safe(s: str) -> str:
    return re.sub(r"[^A-Za-z0-9]+", "_", (s or "")).strip("_").lower() or "obj"


def _snap_base(obj: DmsScObject) -> str:
    """Stable, unique-per-object filename stem (guards against overloaded routines)."""
    parts = [obj.source_type, obj.source_package, obj.source_name]
    stem = _safe("__".join(p for p in parts if p))[:100]
    # Short disambiguator only (not a security/signature use); SHA-256 keeps the
    # scanners quiet and the 8-hex-char stem is just as collision-safe here.
    h = hashlib.sha256(obj.source_id.encode("utf-8")).hexdigest()[:8]
    return f"{stem}__{h}"


def _status_for(disp: str) -> str:
    # Reuse the existing manifest status vocabulary.
    return "needs_human" if disp == MANUAL else "converted"


def run(args) -> int:
    dms_dir = getattr(args, "dms_sc_dir", None)
    if not dms_dir:
        console.err("--dms-sc-dir is required")
        return 2
    try:
        result = parse_project(dms_dir)
    except FileNotFoundError as exc:
        console.err(str(exc))
        return 2
    except Exception as exc:  # noqa: BLE001
        console.err(f"failed to parse DMS SC project: {exc}")
        return 1

    if not result.objects:
        console.warn("no convertible objects found in the DMS SC project "
                     "(check --dms-sc-dir points at the project root)")
        return 0

    # Attach apply-result status by matching the target node id (== Full Path).
    apply_results = load_apply_results(dms_dir)
    if apply_results:
        for o in result.objects:
            rec = apply_results.get((o.target_id or "").upper())
            if rec:
                o.apply_status = rec.get("status", "")
                o.apply_error = rec.get("error", "")

    # Classify everything.
    for o in result.objects:
        classify(o)

    schemas = result.schemas()
    schema_filter = None
    if getattr(args, "schema", None):
        schema_filter = {s.strip().upper() for s in args.schema.split(",") if s.strip()}
        schemas = [s for s in schemas if s.upper() in schema_filter]
        if not schemas:
            console.err(f"schema(s) {sorted(schema_filter)} not found in project. "
                        f"Available: {', '.join(result.schemas()) or '(none)'}")
            return 2

    console.heading("DMS SC import")
    console.info(f"Source engine: {result.source_engine or '?'}  ->  "
                 f"Target engine: {result.target_engine or '?'}")
    console.info(f"Project: {args.project}   Schemas: {', '.join(schemas)}")

    ws_root = config.workspace_dir(args.project)
    grand = Counter()
    schema_stats: List[dict] = []
    for schema in schemas:
        objs = result.for_schema(schema)
        schema_stats.append(_emit_schema(args, ws_root, schema, objs, result, grand))

    # Update the human-readable, phase-aligned migration report (Inception + Validation).
    _update_migration_report(args.project, ws_root, result, schemas, schema_stats, grand)

    console.heading("Import summary")
    total = sum(grand[k] for k in (ACCEPT, VERIFY, MANUAL))
    console.ok(f"{total} object(s) across {len(schemas)} schema(s): "
               f"ACCEPT={grand[ACCEPT]}  VERIFY={grand[VERIFY]}  MANUAL={grand[MANUAL]}")
    console.ok(f"Migration report: {report.report_path(args.project)}")
    console.info("Next: review the classification report(s), then run `diff-target` "
                 "(Phase 2) to reconcile against the live target. MANUAL objects go "
                 "through convert-code; VERIFY objects through gen-tests/run-tests.")
    return 0


def _update_migration_report(project: str, ws_root: Path, result: ImportResult,
                             schemas: List[str], schema_stats: List[dict],
                             grand: Counter) -> None:
    from ..dmssc import verification as ver
    tot_apply_err = sum(s["apply_errors"] for s in schema_stats)
    manual_all = [m for s in schema_stats for m in s["manual_objects"]]

    lines = [
        f"## {report.PHASE_TITLE[report.INCEPTION]}",
        "",
        "### Entry path: imported an existing AWS DMS Schema Conversion (DMS SC) project",
        "",
        f"- Source **{result.source_engine or '?'}** → Target "
        f"**{result.target_engine or '?'}**",
        f"- Project workspace: `{ws_root}`",
        f"- Schemas imported: {', '.join(schemas)}",
        "",
        "Every converted object was triaged into one of three dispositions:",
        "",
        "| Schema | Objects | ACCEPT (keep as-is) | VERIFY (prove) | MANUAL (reconvert) |",
        "|---|---|---|---|---|",
    ]
    for s in schema_stats:
        lines.append(f"| {s['schema']} | {s['total']} | {s['accept']} "
                     f"| {s['verify']} | {s['manual']} |")
    lines.append(f"| **All** | **{sum(s['total'] for s in schema_stats)}** "
                 f"| **{grand[ACCEPT]}** | **{grand[VERIFY]}** | **{grand[MANUAL]}** |")
    lines += [
        "",
        "### What you should be aware of",
        "",
        f"- **{grand[MANUAL]} object(s) need manual reconversion** (CRITICAL/HIGH action "
        "items or explicit \"convert manually\" instructions). They are marked "
        "`needs_human` in the code manifest and must be converted before use"
        + (":" if manual_all else "."),
    ]
    for m in manual_all[:20]:
        lines.append(f"  - `{m}`")
    lines += [
        f"- **{grand[VERIFY]} object(s) are probabilistic (GenAI/ML) or advisory "
        "conversions** kept from DMS SC — they must be proven equivalent and marked "
        "verified (see the Validation section).",
        f"- **{grand[ACCEPT]} object(s) were accepted as-is** (no action items).",
    ]
    if tot_apply_err:
        lines.append(
            f"- **{tot_apply_err} object(s) reported an apply ERROR in DMS SC** (e.g. "
            "foreign keys that did not apply to the target). These will be reconciled by "
            "`diff-target` and recreated during the load phase — do not assume the target "
            "is complete.")
    lines += [
        "",
        "### Artifacts",
        "",
        "- Triage report per schema: `01-assessment/dms-sc-classification-<SCHEMA>.md`",
        "- Full mapping + classification: `01-assessment/dms-sc-map-<SCHEMA>.json`",
        "- DDL snapshots: `01-assessment/dms-sc/<SCHEMA>/{source,target}/*.sql`",
        "- Code manifest (DMS SC output pre-loaded): "
        "`02-construction/code-manifest-<SCHEMA>.yaml`",
        "",
        "### Next steps",
        "",
        "1. Review the per-schema triage reports.",
        "2. Run `diff-target` to reconcile every object against the **live** target "
        "(resolve conflicts). *(Phase 2 — in progress)*",
        "3. Reconvert MANUAL objects with `convert-code` → `apply-schema --code`.",
        "4. Prove VERIFY objects with `gen-tests` / `run-tests`, then record verdicts "
        "with `dbmig verify` (tracked in the Validation section).",
        "",
    ]
    report.update_phase(project, report.INCEPTION, "\n".join(lines))

    # Validation section reflects verification progress across all schemas.
    report.update_phase(project, report.VALIDATION, ver.render_validation_section(ws_root))


def _emit_schema(args, ws_root: Path, schema: str, objs: List[DmsScObject],
                 result: ImportResult, grand: Counter) -> dict:
    assess = ws_root / "01-assessment"
    constr = ws_root / "02-construction"
    snap_src = assess / "dms-sc" / schema / "source"
    snap_tgt = assess / "dms-sc" / schema / "target"
    for d in (snap_src, snap_tgt):
        d.mkdir(parents=True, exist_ok=True)

    target_schema = next((o.target_schema for o in objs if o.target_schema),
                         schema.lower())
    code_dir = constr / "code" / target_schema.lower()

    counts = Counter()
    code_units: List[dict] = []

    for o in objs:
        counts[o.disposition] += 1
        grand[o.disposition] += 1
        base = _snap_base(o)
        # DDL snapshots (all objects)
        if o.source_ddl:
            p = snap_src / f"{base}.sql"
            p.write_text(o.source_ddl)
            o.source_ddl_ref = str(p.relative_to(ws_root))
        if o.target_ddl:
            p = snap_tgt / f"{base}.sql"
            p.write_text(o.target_ddl)
            o.target_ddl_ref = str(p.relative_to(ws_root))

        # Code objects also get a construction manifest unit + output file.
        if o.category == "code":
            code_dir.mkdir(parents=True, exist_ok=True)
            out_rel = f"code/{target_schema.lower()}/{base}.sql"
            if o.target_ddl:
                (constr / out_rel).write_text(o.target_ddl)
            unit = {
                "name": o.target_name or o.source_name,
                "object_type": o.source_type,
                "schema": schema,
                "prompt_file": "",
                "output_file": out_rel,
                "status": _status_for(o.disposition),
                "origin": "dms_sc",
                "disposition": o.disposition,
                "source_id": o.source_id,
                "target_name": o.target_name,
                "target_type": o.target_type,
                "has_genai": o.has_genai,
                "dms_apply_status": o.apply_status or None,
                "action_items": [a.to_dict() for a in o.action_items],
            }
            if o.disposition == VERIFY:
                unit["needs_verification"] = True
            if o.disposition == MANUAL:
                unit["needs_manual_conversion"] = True
            code_units.append(unit)

    # ---- code manifest --------------------------------------------------------
    if code_units:
        manifest = {
            "project": args.project,
            "schema": schema,
            "phase": "construction-code",
            "origin": "dms_sc",
            "generated_at": _now(),
            "provider": "dms_sc",
            "model": result.target_engine or "aws-dms-sc",
            "unit_count": len(code_units),
            "units": code_units,
        }
        mpath = config.resolve_manifest(constr, "code-manifest", schema, for_write=True)
        constr.mkdir(parents=True, exist_ok=True)
        write_manifest(mpath, manifest)

    # ---- verification ledger (VERIFY objects; merge-preserve across re-imports) --
    from ..dmssc import verification as ver
    verify_objs = [o for o in objs if o.disposition == VERIFY]
    lpath = ver.ledger_path(ws_root, schema)
    ledger = ver.load_ledger(lpath)
    added = ver.merge_pending(ledger, args.project, schema, verify_objs)
    if verify_objs:
        ver.save_ledger(lpath, ledger)
    vsum = ver.summary(ledger)

    # ---- sidecar map (leaf-granular source of truth) --------------------------
    sidecar = {
        "project": args.project,
        "schema": schema,
        "target_schema": target_schema,
        "source_engine": result.source_engine,
        "target_engine": result.target_engine,
        "dms_sc_dir": result.dms_sc_dir,
        "generated_at": _now(),
        "counts": {ACCEPT: counts[ACCEPT], VERIFY: counts[VERIFY], MANUAL: counts[MANUAL]},
        "verification": vsum,
        "objects": [o.to_dict() for o in objs],
    }
    assess.mkdir(parents=True, exist_ok=True)
    (assess / f"dms-sc-map-{schema}.json").write_text(json.dumps(sidecar, indent=2))

    # ---- human classification report -----------------------------------------
    ver_status = {sid: e.get("status", ver.PENDING)
                  for sid, e in ledger.get("items", {}).items()}
    (assess / f"dms-sc-classification-{schema}.md").write_text(
        _report_md(args.project, schema, target_schema, objs, counts, result, ver_status))

    console.ok(f"[{schema}] {sum(counts.values())} object(s): "
               f"ACCEPT={counts[ACCEPT]} VERIFY={counts[VERIFY]} MANUAL={counts[MANUAL]}"
               + (f"  ({len(code_units)} code unit(s))" if code_units else ""))

    return {
        "schema": schema,
        "target_schema": target_schema,
        "total": sum(counts.values()),
        "accept": counts[ACCEPT],
        "verify": counts[VERIFY],
        "manual": counts[MANUAL],
        "code_units": len(code_units),
        "apply_errors": sum(1 for o in objs if (o.apply_status or "").upper() == "ERROR"),
        "manual_objects": [f"{o.source_schema}.{o.source_name}" for o in objs
                           if o.disposition == MANUAL],
        "verification": vsum,
        "verify_added": added,
    }


def _report_md(project: str, schema: str, target_schema: str,
               objs: List[DmsScObject], counts: Counter, result: ImportResult,
               ver_status: dict) -> str:
    by_cat = Counter(o.category for o in objs)
    lines = [
        f"# DMS SC import — triage for schema `{schema}`",
        "",
        f"- Project: **{project}**",
        f"- Source: **{result.source_engine or '?'}** → Target: "
        f"**{result.target_engine or '?'}** (target schema `{target_schema}`)",
        f"- Objects: **{sum(counts.values())}** "
        f"(storage={by_cat.get('storage',0)}, code={by_cat.get('code',0)}, "
        f"other={by_cat.get('other',0)+by_cat.get('server',0)})",
        "",
        "## Disposition",
        "",
        "| Disposition | Count | Meaning |",
        "|---|---|---|",
        f"| ACCEPT | {counts[ACCEPT]} | keep the DMS SC conversion as-is |",
        f"| VERIFY | {counts[VERIFY]} | keep, but prove with equivalence tests (gen-tests/run-tests) |",
        f"| MANUAL | {counts[MANUAL]} | must be reconverted (convert-code) |",
        "",
        "> **Policy:** MANUAL = any action item of severity CRITICAL/HIGH, or an explicit "
        "\"convert your source code manually\" / method-stub instruction. VERIFY = any "
        "remaining action item (incl. `5444` ML/GenAI and LOW/MEDIUM advisories) or a "
        "GenAI-generated span. ACCEPT = no action items. Tune in `dbmig/dmssc/classify.py`.",
        "",
    ]
    for disp, title in ((MANUAL, "MANUAL — reconvert"),
                        (VERIFY, "VERIFY — keep + prove"),
                        (ACCEPT, "ACCEPT — keep as-is")):
        group = [o for o in objs if o.disposition == disp]
        if not group:
            continue
        lines += [f"## {title} ({len(group)})", ""]
        if disp == ACCEPT:
            lines.append("| Object | Type | Applied |")
            lines.append("|---|---|---|")
            for o in sorted(group, key=lambda x: (x.source_type, x.source_name)):
                lines.append(f"| `{o.source_schema}.{o.source_name}` | {o.source_type} "
                             f"| {o.apply_status or '-'} |")
        else:
            verify_col = disp == VERIFY
            head = "| Object | Type | GenAI | Applied | Action items |"
            sep = "|---|---|---|---|---|"
            if verify_col:
                head = "| Object | Type | Verified | GenAI | Applied | Action items |"
                sep = "|---|---|---|---|---|---|"
            lines.append(head)
            lines.append(sep)
            for o in sorted(group, key=lambda x: (x.source_type, x.source_name)):
                ais = "; ".join(
                    f"{a.code}/{a.severity or '?'}"
                    + (f" {a.action}" if a.action else "")
                    for a in o.action_items) or "-"
                ais = ais.replace("\n", " ").replace("|", "\\|")
                if len(ais) > 300:
                    ais = ais[:300] + "…"
                genai = "yes" if o.has_genai else "-"
                if verify_col:
                    vst = ver_status.get(o.source_id, "pending")
                    badge = {"verified": "✅ verified", "failed": "❌ failed"}.get(
                        vst, "⏳ pending")
                    lines.append(
                        f"| `{o.source_schema}.{o.source_name}` | {o.source_type} "
                        f"| {badge} | {genai} | {o.apply_status or '-'} | {ais} |")
                else:
                    lines.append(
                        f"| `{o.source_schema}.{o.source_name}` | {o.source_type} "
                        f"| {genai} | {o.apply_status or '-'} | {ais} |")
        lines.append("")

    if result.unmatched_action_items:
        lines += ["## Unmatched action items (schema/column level)", "",
                  "Action items reported against nodes that did not map to a parsed "
                  "object (e.g. column- or schema-level). Review manually.", ""]
        for name, items in result.unmatched_action_items.items():
            codes = ", ".join(sorted({a.code for a in items}))
            lines.append(f"- `{name}` — codes: {codes}")
        lines.append("")
    return "\n".join(lines) + "\n"
