"""``dbmig apply-schema`` — apply converted DDL to the PostgreSQL target.

Status-aware and resumable: units already ``applied`` are skipped, so re-running
after a fix never re-triggers "already exists" on previously-applied objects.

Error-retry loop (minimizes human-in-the-loop): when a unit fails to apply, the
PostgreSQL error is captured and a **remediation prompt** is written for that unit
(the original conversion prompt + the failed DDL + the exact error). Kiro
re-converts the unit from that prompt, then apply-schema is re-run. This repeats
up to ``llm.max_retries`` attempts per unit:

  - failing units below the limit are marked ``failed`` (retryable) and the
    command prints ``RETRY_AVAILABLE``;
  - units that reach the limit are marked ``needs_human`` and the command prints
    ``MAX_RETRIES_EXHAUSTED``.

The db-migration-construction skill drives the loop: convert → apply → while the
output says RETRY_AVAILABLE, re-convert the failed units from their ``.retry.md``
and apply again, stopping on success or MAX_RETRIES_EXHAUSTED.
"""
from __future__ import annotations

from pathlib import Path
from typing import List, Tuple

import yaml

from .. import config, console, engines, followup as fu
from ..connections import load_pair
from ..conversion import ddl_split, output_parser, prompt_builder
from ..manifest import load_manifest, write_manifest


def _retry_dir(ws: Path, code: bool) -> Path:
    d = ws / ("retries_code" if code else "retries")
    d.mkdir(parents=True, exist_ok=True)
    return d


def run(args) -> int:
    try:
        pair = load_pair()
    except config.ConfigError as exc:
        console.err(str(exc))
        return 2
    if "target" not in pair:
        console.err("apply-schema requires a 'target' connection")
        return 2
    try:
        target = engines.get_target_engine(pair)
    except config.ConfigError as exc:
        console.err(str(exc))
        return 2

    ws = config.workspace_dir(args.project) / "02-construction"
    manifest_path = config.resolve_manifest(
        ws, "code-manifest" if args.code else "manifest", args.schema)
    if not manifest_path.exists():
        console.err(f"manifest not found: {manifest_path} "
                    f"(run convert-{'code' if args.code else 'schema'} first)")
        return 2
    manifest = load_manifest(manifest_path)
    units = manifest.get("units", [])

    # Phase: by default apply pre-data DDL (tables/indexes/PK/UK/CHECK/functions)
    # and defer foreign keys + triggers; --post-data applies only those deferred
    # statements, after the data load. They are tracked in separate manifest
    # fields so each phase is independently idempotent/resumable.
    post = bool(getattr(args, "post_data", False))
    if post and args.code:
        console.err("--post-data applies to schema foreign keys/triggers, not code "
                    "objects; drop --code")
        return 2
    status_field = "post_status" if post else "status"
    attempts_field = "post_attempts" if post else "attempts"
    err_field = "post_last_error" if post else "last_error"
    retry_field = "post_retry_prompt" if post else "retry_prompt"
    phase_label = ("post-data (FK + triggers)" if post
                   else "code" if args.code else "pre-data")

    # max_retries: CLI override wins over config.
    max_retries = int(config.llm_config().get("max_retries", 3))
    if getattr(args, "max_retries", None) is not None:
        max_retries = int(args.max_retries)
    max_retries = max(1, max_retries)

    mode = fu.resolve_mode(args, config.load_migration_config())
    followup = fu.FollowUp(args.project)

    tables = None
    if getattr(args, "tables", None):
        tables = {t.strip().upper() for t in args.tables.split(",") if t.strip()}

    # Build work list: units with a converted output file, not already applied,
    # not already exhausted (needs_human), honoring an optional --tables filter.
    work: List[Tuple[str, str]] = []
    skipped_applied = 0
    skipped_exhausted = 0
    missing = 0
    not_structural = 0
    no_postdata = 0
    for u in units:
        if tables and u["name"].upper() not in tables:
            continue
        # post-data requires the unit's pre-data DDL to be applied first
        if post and u.get("status") != "applied":
            not_structural += 1
            continue
        if u.get(status_field) == "applied":
            skipped_applied += 1
            continue
        if u.get(status_field) == "needs_human":
            skipped_exhausted += 1
            continue
        out_path = ws / u["output_file"]
        if not out_path.exists():
            if not post:
                u["status"] = "pending"
            missing += 1
            continue
        full = output_parser.parse_ddl(out_path.read_text())
        pre_sql, post_sql = ddl_split.partition_ddl(full)
        sql = post_sql if post else pre_sql
        if not sql.strip():
            if post:
                # nothing to defer for this unit (no FK / trigger) -> trivially done
                u["post_status"] = "applied"
                no_postdata += 1
            else:
                u["status"] = "empty"
            continue
        work.append((u["name"], sql))

    if skipped_applied:
        console.info(f"skipping {skipped_applied} already-applied unit(s)")
    if not_structural:
        console.warn(f"{not_structural} unit(s) not yet structurally applied — run "
                     "apply-schema (pre-data) before --post-data")
    if no_postdata:
        console.info(f"{no_postdata} unit(s) have no foreign keys/triggers to defer")
    if skipped_exhausted:
        console.warn(f"{skipped_exhausted} unit(s) marked needs_human (max retries "
                     "exhausted) — skipped; resolve manually then re-run")
    if missing:
        console.warn(f"{missing} unit(s) not yet converted (no output file) — "
                     "have Kiro convert them first")
    if not work:
        if skipped_exhausted:
            console.err("MAX_RETRIES_EXHAUSTED: remaining failures recorded for "
                        f"follow-up ({followup.open_count()} open). See {followup.md.name}")
            return 1 if mode == fu.INTERACTIVE else 0
        console.ok("nothing to apply (all units already applied)")
        return 0

    schema = manifest.get("schema", args.schema or "").lower()

    if getattr(args, "dry_run", False):
        console.heading(f"DRY RUN — {phase_label}: {len(work)} unit(s) would be applied"
                        + (f" into schema {schema}" if schema else ""))
        for label, sql in work:
            console.info(f"--- {label} ---")
            print(sql.rstrip() + "\n")
        console.ok("dry-run: nothing was applied to the target.")
        return 0

    console.info(f"Applying {phase_label} for {len(work)} unit(s) to the target ...")
    misplaced_warning = None
    try:
        if schema:
            target.ensure_schema(schema)
        results = target.apply_units(work)
        # Post-apply verification (schema pass only): a unit whose DDL is qualified
        # with the WRONG schema/database applies cleanly and reports success — the
        # failure only surfaces later, at the data load. Check the catalog now.
        # (Learned from a real oracle->mysql run where DDL qualified with the
        # connection's database name landed every table outside the derived schema.)
        if schema and not args.code:
            applied_names = [r["label"] for r in results if r["status"] == "applied"]
            if applied_names:
                found, missing, unknown = 0, [], False
                for name in applied_names:
                    ok = target.table_exists(schema, name.lower())
                    if ok is None:
                        unknown = True
                        break
                    if ok:
                        found += 1
                    else:
                        missing.append(name)
                if not unknown and found == 0:
                    misplaced_warning = (
                        f"apply reported {len(applied_names)} unit(s) applied, but NONE of "
                        f"their tables exist in target schema '{schema}'. The DDL is almost "
                        f"certainly qualified with a different schema/database (e.g. the "
                        f"connection's database name). The target schema is derived from the "
                        f"SOURCE schema, lower-cased: qualify objects with '{schema}'.")
                elif not unknown and missing:
                    misplaced_warning = (
                        f"{len(missing)} applied unit(s) have no table in target schema "
                        f"'{schema}': {', '.join(missing[:5])}"
                        f"{' …' if len(missing) > 5 else ''} — check the DDL's schema "
                        f"qualification.")
    except Exception as exc:  # noqa: BLE001
        console.err(f"apply failed: {exc}")
        return 1
    finally:
        target.close()

    if misplaced_warning:
        console.err(f"SCHEMA MISMATCH: {misplaced_warning}")
        followup.record(phase="construction", kind="schema_mismatch",
                        obj=f"schema {schema}", detail=misplaced_warning)

    status_by_name = {r["label"]: r for r in results}
    retry_dir = _retry_dir(ws, args.code)
    applied = 0
    retryable: List[str] = []
    exhausted: List[str] = []

    for u in units:
        r = status_by_name.get(u["name"])
        if not r:
            continue
        if r["status"] == "applied":
            u[status_field] = "applied"
            u[err_field] = None
            applied += 1
            continue
        # failed this round → record + decide retry vs exhausted
        attempts = int(u.get(attempts_field, 0)) + 1
        u[attempts_field] = attempts
        u[err_field] = r["error"]
        if attempts >= max_retries:
            u[status_field] = "needs_human"
            exhausted.append(u["name"])
            followup.record(
                phase="construction", kind="conversion_failure", obj=u["name"],
                detail=r.get("error") or "apply failed after max retries",
                extra={"attempts": attempts, "phase": phase_label,
                       "output_file": u.get("output_file")})
        else:
            u[status_field] = "failed"
            retryable.append(u["name"])
            # Write a remediation prompt: original prompt + failed DDL + the error.
            try:
                original = (ws / u["prompt_file"]).read_text()
            except OSError:
                original = ""
            try:
                previous = (ws / u["output_file"]).read_text()
            except OSError:
                previous = ""
            retry_text = prompt_builder.build_retry_prompt(
                original, previous, r["error"] or "", attempts + 1, max_retries)
            sub = retry_dir / str(u.get("schema", "")).upper()
            sub.mkdir(parents=True, exist_ok=True)
            retry_path = sub / f"{u['name']}.retry.md"
            retry_path.write_text(retry_text)
            u[retry_field] = str(retry_path.relative_to(ws))

    manifest["units"] = units
    manifest["max_retries"] = max_retries
    write_manifest(manifest_path, manifest)

    if post:
        report_path = ws / config.manifest_file("apply_report_postdata", args.schema)
    else:
        report_path = ws / config.manifest_file(
            "apply_report_code" if args.code else "apply_report", args.schema)
    report_path.write_text(yaml.safe_dump({"results": results}, sort_keys=False))

    console.heading(f"Apply results — {phase_label}")
    console.ok(f"applied: {applied}/{len(work)}")

    if not retryable and not exhausted:
        console.ok(f"All units applied. Report: {report_path}")
        return 0

    if exhausted:
        console.err(f"needs_human: {len(exhausted)} unit(s) hit max_retries "
                    f"({max_retries}): {', '.join(exhausted[:20])}")
    if retryable:
        console.err(f"failed (retryable): {len(retryable)} unit(s): "
                    f"{', '.join(retryable[:20])}")
        for name in retryable[:20]:
            console.err(f"  {name}: {status_by_name[name]['error']}")
        console.info(f"Remediation prompts written to: {retry_dir}")
        console.info(
            "RETRY_AVAILABLE: re-convert each failed unit from its .retry.md "
            "(write corrected DDL to the unit's output_file), then re-run: "
            f"dbmig apply-schema --schema {args.schema} --project {args.project}"
            + (" --code" if args.code else "")
            + (" --post-data" if post else ""))
        return 1

    # only exhausted, nothing retryable
    console.err("MAX_RETRIES_EXHAUSTED: failures recorded for follow-up "
                f"({followup.open_count()} open) — see {followup.md.name}; "
                f"per-unit last_error in {report_path.name}")
    if mode == fu.INTERACTIVE:
        return 1
    console.info("silent mode: continuing without blocking; resolve follow-up items later")
    return 0
