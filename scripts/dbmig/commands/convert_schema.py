"""``dbmig convert-schema`` — LLM-driven (Kiro) schema conversion orchestrator.

Phase 1 (Extract) + prompt assembly. This command does NOT call a hosted LLM.
With ``provider: kiro`` (default) it:

  1. extracts Oracle object-units (table + indexes + constraints + FKs +
     triggers + comments/grants),
  2. batches small tables together to reduce round-trips,
  3. writes a prompt bundle per batch (with skill + playbook context injected),
  4. writes a manifest tracking each unit's status,

then hands off to the Kiro db-migration-construction skill, which reads each
prompt, writes PostgreSQL DDL to the unit's output file, and marks it converted.
``dbmig apply-schema`` then applies the DDL to the target.
"""
from __future__ import annotations

import datetime as _dt
from pathlib import Path
from typing import List

import yaml

from .. import config, console
from ..connections import load_pair
from .. import engines
from ..conversion import prompt_builder
from ..conversion.llm_client import make_client, HandoffRequired
# Manifest I/O lives in the shared module; re-exported here for backwards
# compatibility with callers that historically imported it from this command.
from ..manifest import load_manifest, write_manifest  # noqa: F401


def _now() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _target_label() -> str:
    """Display name of the active pair's TARGET engine (PostgreSQL / MySQL), so the
    conversion hand-off messages name the correct engine instead of hardcoding one."""
    try:
        target = config.active_pair().split("-to-")[-1]
    except Exception:
        target = "postgresql"
    return {"postgresql": "PostgreSQL", "mysql": "MySQL"}.get(target, target or "target")


def run(args) -> int:
    try:
        pair = load_pair()
        source = engines.get_source_engine(pair)
    except config.ConfigError as exc:
        console.err(str(exc))
        return 2

    mig_cfg = config.load_migration_config()
    llm_cfg = config.llm_config(mig_cfg)
    try:
        client = make_client(llm_cfg)
    except ValueError as exc:
        console.err(str(exc))
        return 2

    tables = None
    if getattr(args, "tables", None):
        tables = [t.strip() for t in args.tables.split(",") if t.strip()]

    console.info(f"Extracting object-units for schema {args.schema} ...")
    try:
        units = source.extract_units(args.schema, tables=tables)
    except Exception as exc:  # noqa: BLE001
        console.err(f"extraction failed: {exc}")
        return 1
    finally:
        source.close()

    if not units:
        console.warn("no tables found to convert")
        return 0

    batches = engines.batch_units(
        units,
        row_threshold=int(llm_cfg.get("batch_row_threshold", 100000)),
        max_units=int(llm_cfg.get("batch_max_units", 5)),
    )

    root = config.find_repo_root()
    ws = config.workspace_dir(args.project) / "02-construction"
    prompts_dir = ws / "prompts" / args.schema.upper()
    ddl_dir = ws / "ddl" / args.schema.lower()
    prompts_dir.mkdir(parents=True, exist_ok=True)
    ddl_dir.mkdir(parents=True, exist_ok=True)

    manifest_units: List[dict] = []
    tdisp = _target_label()
    for i, batch in enumerate(batches, start=1):
        if len(batch) == 1:
            prompt_name = f"{batch[0].name}.prompt.md"
        else:
            prompt_name = f"batch_{i:03d}.prompt.md"
        prompt_path = prompts_dir / prompt_name

        outputs = [f"ddl/{args.schema.lower()}/{u.name.lower()}.sql" for u in batch]
        prompt_body = prompt_builder.build_unit_prompt(batch, repo_root=root)
        header = (
            f"<!-- dbmig conversion prompt bundle\n"
            f"     batch: {i}/{len(batches)}  units: "
            f"{', '.join(u.name for u in batch)}\n"
            f"     Convert each unit and SAVE {tdisp} DDL to its output file:\n"
            + "".join(f"       - {u.name} -> {o}\n" for u, o in zip(batch, outputs))
            + f"     Then set the unit's status to 'converted' in "
            f"{config.manifest_file('manifest', args.schema)}. -->\n\n"
        )
        prompt_path.write_text(header + prompt_body)

        for u, out in zip(batch, outputs):
            manifest_units.append({
                "name": u.name,
                "schema": u.schema,
                "num_rows": u.num_rows,
                "batch_id": i,
                "prompt_file": str(prompt_path.relative_to(ws)),
                "output_file": out,
                "status": "pending",
            })

    manifest = {
        "project": args.project,
        "schema": args.schema.upper(),
        "phase": "construction",
        "generated_at": _now(),
        "provider": client.provider,
        "model": llm_cfg.get("model"),
        "unit_count": len(manifest_units),
        "batch_count": len(batches),
        "units": manifest_units,
    }
    manifest_path = config.resolve_manifest(ws, "manifest", args.schema, for_write=True)
    _warn_if_reusing_workspace(manifest_path, console, yaml)
    write_manifest(manifest_path, manifest)

    console.heading("Schema conversion prepared")
    console.ok(f"{len(units)} object-units in {len(batches)} batch(es)")
    console.ok(f"Prompt bundles: {prompts_dir}")
    console.ok(f"Manifest:       {manifest_path}")

    # Hand-off behavior: the Kiro construction skill performs the conversion.
    try:
        client.convert("")  # KiroHandoffClient signals hand-off
    except HandoffRequired:
        console.info(
            "Provider 'kiro': conversion is performed by Kiro. In the "
            "db-migration-construction skill, read each prompt bundle, write the "
            f"{tdisp} DDL to each unit's output_file, and set status to "
            "'converted' in the manifest. Then run: dbmig apply-schema "
            f"--schema {args.schema} --project {args.project}")
    return 0


def _warn_if_reusing_workspace(manifest_path, console, yaml):
    """Warn when regenerating a manifest that shows prior progress.

    Reusing a --project across runs silently mixes artifacts (and follow-up items)
    from different runs/targets in one workspace — seen in a real workspace where a
    June run's test failures sat beside an August run's reports. The README's
    convention is a unique project per run (e.g. date-stamped); this warning makes
    the reuse visible instead of silent."""
    if not manifest_path.exists():
        return
    try:
        prev = yaml.safe_load(manifest_path.read_text()) or {}
    except Exception:
        return
    units = prev.get("units") or []
    progressed = [u for u in units
                  if u.get("status") not in (None, "pending")
                  or u.get("post_status") not in (None, "pending")]
    if progressed:
        console.warn(
            f"overwriting existing manifest {manifest_path.name} in which "
            f"{len(progressed)}/{len(units)} unit(s) had progressed (converted/applied). "
            f"If this is a NEW run (different target or a re-run), prefer a fresh "
            f"--project name — reusing one mixes runs' artifacts and follow-up items "
            f"in a single workspace. Generated at: {prev.get('generated_at', '?')}.")
