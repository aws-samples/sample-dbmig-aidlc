"""``dbmig mark`` — set manifest unit statuses.

A small helper for the Kiro conversion loop: after writing the converted DDL /
code / test specs, flip the affected units' ``status`` in the schema-scoped
manifest without hand-editing YAML. Targets the schema manifest by default, or
the code/test manifest with ``--code`` / ``--tests``.
"""
from __future__ import annotations

from pathlib import Path
from typing import List, Optional

from .. import config, console
from ..manifest import load_manifest, write_manifest


def apply_status(manifest: dict, status: str, *, only: Optional[List[str]] = None,
                 ws: Optional[Path] = None, require_output: bool = False) -> int:
    """Set ``status`` on matching units in ``manifest``; return the count changed.

    ``only`` limits to the named units (case-insensitive). ``require_output`` only
    marks units whose ``output_file``/``spec_file`` exists under ``ws``. Pure and
    side-effect-free on disk (the caller persists the manifest)."""
    names = {n.upper() for n in (only or [])}
    changed = 0
    for u in manifest.get("units", []):
        if names and str(u.get("name", "")).upper() not in names:
            continue
        if require_output:
            rel = u.get("output_file") or u.get("spec_file")
            if not rel or ws is None or not (ws / rel).exists():
                continue
        if u.get("status") != status:
            u["status"] = status
            changed += 1
    return changed


def _base_for(args) -> str:
    if getattr(args, "code", False):
        return "code-manifest"
    if getattr(args, "tests", False):
        return "test-manifest"
    return "manifest"


def _phase_dir(args) -> str:
    return "03-validation" if getattr(args, "tests", False) else "02-construction"


def run(args) -> int:
    ws = config.workspace_dir(args.project) / _phase_dir(args)
    base = _base_for(args)
    manifest_path = config.resolve_manifest(ws, base, args.schema)
    if not manifest_path.exists():
        console.err(f"manifest not found: {manifest_path}")
        return 2
    manifest = load_manifest(manifest_path)
    only = [t.strip() for t in (getattr(args, "only", None) or "").split(",") if t.strip()]
    changed = apply_status(
        manifest, args.status, only=only or None, ws=ws,
        require_output=getattr(args, "only_existing_output", False))
    write_manifest(manifest_path, manifest)
    console.ok(f"marked {changed} unit(s) as '{args.status}' in {manifest_path.name}")
    return 0
