"""``dbmig convert-code`` — convert PL/SQL code objects (separate pass).

Packages, procedures, functions, and types need different context and often an
iterative conversation with the LLM (Kiro), so they are handled after the
table object-units. Same hand-off model as convert-schema.
"""
from __future__ import annotations

import datetime as _dt
from typing import List

import yaml

from .. import config, console, engines, followup as fu
from ..connections import load_pair
from ..conversion import naming, prompt_builder
from ..conversion.llm_client import make_client, HandoffRequired
from ..manifest import write_manifest


def _now() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _safe(name: str) -> str:
    return name.lower().replace(" ", "_")


def _check_naming_conflicts(routines, project: str) -> None:
    """Flag package subprograms whose flattened ``<package>_<subprogram>`` name
    is not unique (the underscore-join is ambiguous). Collisions are recorded to
    the project follow-up log so they are resolved before the run is trusted."""
    conflicts = naming.find_flatten_conflicts(routines)
    if not conflicts:
        return
    collisions = [c for c in conflicts if c["kind"] == "collision"]
    overloads = [c for c in conflicts if c["kind"] == "overload"]

    if collisions:
        followup = fu.FollowUp(project)
        console.warn(
            f"{len(collisions)} package-flattening NAME COLLISION(s): different "
            "Oracle routines map to the same '<package>_<subprogram>' PostgreSQL "
            "name (the underscore join is ambiguous).")
        for c in collisions:
            tag = "  [shadows a standalone routine]" if c["involves_standalone"] else ""
            console.err(f"  {c['flattened']}  <=  {', '.join(c['sources'])}{tag}")
            followup.record(
                phase="construction", kind="naming_conflict", obj=c["flattened"],
                detail=("Multiple Oracle routines flatten to the same PostgreSQL "
                        f"name '{c['flattened']}': {', '.join(c['sources'])}. "
                        "Disambiguate (e.g. use a distinct separator such as '$', "
                        "or rename the converted routine)."),
                extra={"sources": c["sources"],
                       "involves_standalone": c["involves_standalone"]})
        console.info(f"Recorded {len(collisions)} naming conflict(s) to follow-up; "
                     "resolve before relying on the converted code.")

    if overloads:
        console.warn(
            f"{len(overloads)} overloaded package subprogram(s) share a flattened "
            "name — ensure the PostgreSQL functions differ by argument signature "
            "(overloading) or rename:")
        for c in overloads:
            console.info(f"  {c['flattened']}  ({c['overloads']} overloads of "
                         f"{c['sources'][0]})")


def merge_spec_and_body(objs):
    """Convert a PACKAGE (or TYPE) and its BODY as ONE unit.

    Oracle's DBMS_METADATA.GET_DDL('PACKAGE'|'TYPE') already returns the spec AND
    the body, so a separate BODY unit re-sent the body in a second prompt (and
    split one logical conversion across two outputs). When the spec's DDL contains
    its body, the separate BODY unit is dropped and the combined unit takes the
    BODY's position in the dependency order (bodies may reference anything).
    Returns ``(objs, merged)`` where ``merged`` maps type -> set of names."""
    import re as _re
    pairs = {"PACKAGE BODY": "PACKAGE", "TYPE BODY": "TYPE"}
    specs = {(o.object_type, o.name): o for o in objs if o.object_type in pairs.values()}
    merged = {}
    out = []
    for o in objs:
        if o.object_type in pairs.values():
            body_type = next(b for b, sp in pairs.items() if sp == o.object_type)
            has_body_unit = any(x.object_type == body_type and x.name == o.name for x in objs)
            if has_body_unit and _re.search(rf"\b{body_type}\b", o.source_ddl, _re.I):
                continue                      # emitted at the BODY's position
            out.append(o)
        elif o.object_type in pairs:
            spec = specs.get((pairs[o.object_type], o.name))
            if spec is not None and _re.search(rf"\b{o.object_type}\b",
                                               spec.source_ddl, _re.I):
                out.append(spec)
                merged.setdefault(spec.object_type, set()).add(spec.name)
            else:
                out.append(o)
        else:
            out.append(o)
    return out, merged


def run(args) -> int:
    try:
        pair = load_pair()
        source = engines.get_source_engine(pair)
    except config.ConfigError as exc:
        console.err(str(exc))
        return 2

    llm_cfg = config.llm_config()
    try:
        client = make_client(llm_cfg)
    except ValueError as exc:
        console.err(str(exc))
        return 2

    console.info(f"Extracting PL/SQL code objects for schema {args.schema} ...")
    try:
        objs = source.extract_code_objects(args.schema)
        routines = source.package_routines(args.schema)
    except Exception as exc:  # noqa: BLE001
        console.err(f"extraction failed: {exc}")
        return 1
    finally:
        source.close()

    if not objs:
        console.warn("no PL/SQL code objects found")
        return 0

    _check_naming_conflicts(routines, args.project)
    objs, merged = merge_spec_and_body(objs)

    root = config.find_repo_root()
    ws = config.workspace_dir(args.project) / "02-construction"
    prompts_dir = ws / "code_prompts" / args.schema.upper()
    code_dir = ws / "code" / args.schema.lower()
    prompts_dir.mkdir(parents=True, exist_ok=True)
    code_dir.mkdir(parents=True, exist_ok=True)

    shared = prompt_builder.write_shared_context(ws, prompt_builder.CODE, root)
    from .convert_schema import _target_label
    from ..engines.base import batch_by_size
    tdisp = _target_label()
    llm = config.llm_config()
    # Small code objects of the same type share one prompt (large ones stay alone),
    # so a schema with thousands of routines does not become thousands of prompts.
    batches = batch_by_size(
        objs, lambda o: len(o.source_ddl),
        max_items=int(llm.get("code_batch_max_units", 8)),
        max_bytes=int(llm.get("code_batch_max_bytes", 12000)),
        key_of=lambda o: o.object_type)
    manifest_units: List[dict] = []
    for i, batch in enumerate(batches, start=1):
        bases = [f"{_safe(o.object_type)}__{_safe(o.name)}" for o in batch]
        outs = [f"code/{args.schema.lower()}/{b}.sql" for b in bases]
        prompt_name = (f"{bases[0]}.prompt.md" if len(batch) == 1
                       else f"batch_{i:04d}.prompt.md")
        prompt_path = prompts_dir / prompt_name
        body = prompt_builder.build_code_prompt(batch, repo_root=root,
                                                shared_context=shared)
        header = (
            f"<!-- dbmig code conversion prompt\n"
            f"     batch: {i}/{len(batches)}\n"
            f"     Convert each object and SAVE {tdisp} code to its output file:\n"
            + "".join(f"       - {o.object_type} {o.schema}.{o.name} -> {out}\n"
                      for o, out in zip(batch, outs))
            + f"     Then set each unit's status to 'converted' in "
            f"{config.manifest_file('code-manifest', args.schema)}. -->\n\n"
        )
        prompt_path.write_text(header + body)
        for obj, out in zip(batch, outs):
            manifest_units.append({
                "name": obj.name,
                "object_type": obj.object_type,
                "schema": obj.schema,
                "batch_id": i,
                "prompt_file": str(prompt_path.relative_to(ws)),
                "output_file": out,
                "status": "pending",
            })
            if obj.name in merged.get(obj.object_type, set()):
                manifest_units[-1]["includes_body"] = True

    manifest = {
        "project": args.project,
        "schema": args.schema.upper(),
        "phase": "construction-code",
        "generated_at": _now(),
        "provider": client.provider,
        "model": llm_cfg.get("model"),
        "unit_count": len(manifest_units),
        "units": manifest_units,
    }
    manifest_path = config.resolve_manifest(ws, "code-manifest", args.schema, for_write=True)
    _warn_if_reusing_workspace(manifest_path, console, yaml)
    write_manifest(manifest_path, manifest)

    console.heading("Code conversion prepared")
    console.ok(f"{len(objs)} code object(s) in {len(batches)} prompt(s)")
    n_merged = sum(len(v) for v in merged.values())
    if n_merged:
        console.info(f"{n_merged} spec+body pair(s) converted as one unit "
                     "(the extracted spec already contains its body)")
    console.ok(f"Prompt bundles: {prompts_dir}")
    console.ok(f"Manifest:       {manifest_path}")
    try:
        client.convert("")
    except HandoffRequired:
        console.info(
            "Provider 'kiro': Kiro converts each code object from its prompt "
            "bundle, writes the output_file, and sets status 'converted'. Code "
            "objects often need iterative review — convert, apply, test, refine.")
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
