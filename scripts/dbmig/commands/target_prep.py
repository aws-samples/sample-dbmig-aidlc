"""Target preparation for a data load into an ALREADY-APPLIED target (Phase 3).

When the target schema already exists (applied by DMS SC, by our own apply-schema, or
pre-created for an AWS DMS task), the load-hostile *secondary* objects — foreign keys,
non-unique secondary indexes, and triggers — should be dropped before a bulk load and
recreated after. Primary keys and UNIQUE constraints are kept (the PK-chunked resumable
copy needs the PK; unique keys are cheap and risky to re-add against loaded data).

Three commands:

- ``capture-target-objects`` — introspect the LIVE target, snapshot ``drop-preload`` +
  ``restore-postload`` scripts and a capture manifest. Read-only (no DB change).
- ``pre-load-drop``  — run the drop script (dry-run by default; ``--apply`` to execute).
- ``post-load-restore`` — run the restore script after the load; then reconcile.

Artifacts live under ``03-validation/target-prep/<SCHEMA>/``. The capture reflects what is
*actually* on the target (including hand edits), which is the correct source of truth per
the design ("always re-diff against live").
"""
from __future__ import annotations

import datetime as _dt
import json
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from .. import config, console, report
from ..connections import load_pair
from .. import engines

_KINDS = ("foreign_keys", "indexes", "triggers")
_KIND_LABEL = {"foreign_keys": "foreign key", "indexes": "index", "triggers": "trigger"}


def _now() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _prep_dir(ws: Path, schema: str) -> Path:
    return ws / "03-validation" / "target-prep" / schema.upper()


def _target(args):
    pair = load_pair()
    target = engines.get_target_engine(pair)
    if not hasattr(target, "capture_secondary_objects"):
        raise config.ConfigError(
            f"target engine '{target.engine}' does not support secondary-object "
            "capture yet (PostgreSQL only for now).")
    return target


def _target_schema(ws: Path, schema: str, fallback_default: Optional[str]) -> str:
    """Prefer the DMS SC map's target_schema, else the connection default, else lower."""
    p = ws / "01-assessment" / f"dms-sc-map-{schema.upper()}.json"
    if p.exists():
        try:
            ts = (json.loads(p.read_text()).get("target_schema") or "").strip()
            if ts:
                return ts
        except Exception:
            pass
    return fallback_default or schema.lower()


# ---- capture --------------------------------------------------------------

def run_capture(args) -> int:
    ws = config.workspace_dir(args.project)
    try:
        target = _target(args)
    except config.ConfigError as exc:
        console.err(str(exc))
        return 2
    default_schema = getattr(target.model, "default_schema", None)
    tschema = _target_schema(ws, args.schema, default_schema)

    try:
        captured = target.capture_secondary_objects(tschema)
    except Exception as exc:  # noqa: BLE001
        console.err(f"capture failed: {exc}")
        return 1
    finally:
        target.close()

    counts = {k: len(captured.get(k, [])) for k in _KINDS}
    d = _prep_dir(ws, args.schema)
    d.mkdir(parents=True, exist_ok=True)

    # capture manifest (source of truth for drop/restore + reconciliation)
    manifest = {
        "project": args.project, "schema": args.schema.upper(),
        "target_schema": tschema, "captured_at": _now(),
        "counts": counts, "objects": captured,
        "drop_state": {}, "restore_state": {},
    }
    (d / "capture.json").write_text(json.dumps(manifest, indent=2))

    # drop script: FKs first, then triggers, then indexes (safe teardown order)
    drop_lines = _script_header("DROP secondary objects BEFORE the data load",
                                tschema, counts)
    for kind in ("foreign_keys", "triggers", "indexes"):
        items = captured.get(kind, [])
        if items:
            drop_lines.append(f"\n-- {_KIND_LABEL[kind]}s ({len(items)})")
            drop_lines += [o["drop_sql"] for o in items]
    (d / f"drop-preload-{args.schema.upper()}.sql").write_text("\n".join(drop_lines) + "\n")

    # restore script: indexes + triggers first, then FKs (FKs after data is present)
    restore_lines = _script_header("RECREATE secondary objects AFTER the data load",
                                   tschema, counts)
    for kind in ("indexes", "triggers", "foreign_keys"):
        items = captured.get(kind, [])
        if items:
            restore_lines.append(f"\n-- {_KIND_LABEL[kind]}s ({len(items)})")
            restore_lines += [o["create_sql"] for o in items]
    (d / f"restore-postload-{args.schema.upper()}.sql").write_text(
        "\n".join(restore_lines) + "\n")

    _update_report(args.project, args.schema, tschema, counts)

    console.heading(f"capture-target-objects — {args.schema} (target `{tschema}`)")
    console.ok(f"captured: {counts['foreign_keys']} FK, {counts['indexes']} index, "
               f"{counts['triggers']} trigger (PK/UNIQUE kept)")
    console.ok(f"scripts: {d}/drop-preload-{args.schema.upper()}.sql , "
               f"restore-postload-{args.schema.upper()}.sql")
    console.info("Next: `pre-load-drop` (before load) then `post-load-restore` (after). "
                 "Both dry-run unless --apply.")
    return 0


def _script_header(title: str, tschema: str, counts: Dict[str, int]) -> List[str]:
    return [
        f"-- dbmig target-prep — {title}",
        f"-- target schema: {tschema}   generated: {_now()}",
        f"-- foreign_keys={counts['foreign_keys']} indexes={counts['indexes']} "
        f"triggers={counts['triggers']}  (primary/unique keys are intentionally kept)",
    ]


# ---- drop / restore -------------------------------------------------------

def run_drop(args) -> int:
    return _execute(args, phase="drop", order=("foreign_keys", "triggers", "indexes"),
                    key="drop_sql", state="drop_state",
                    header="dropping secondary objects (pre-load)")


def run_restore(args) -> int:
    rc = _execute(args, phase="restore",
                  order=("indexes", "triggers", "foreign_keys"),
                  key="create_sql", state="restore_state",
                  header="recreating secondary objects (post-load)")
    if rc == 0 and getattr(args, "apply", False):
        _reconcile(args)
    return rc


def _execute(args, *, phase: str, order: Tuple[str, ...], key: str, state: str,
             header: str) -> int:
    ws = config.workspace_dir(args.project)
    d = _prep_dir(ws, args.schema)
    cap_path = d / "capture.json"
    if not cap_path.exists():
        console.err(f"no capture manifest for schema {args.schema} — run "
                    f"`capture-target-objects` first ({cap_path})")
        return 2
    manifest = json.loads(cap_path.read_text())
    apply = getattr(args, "apply", False)

    try:
        target = _target(args)
    except config.ConfigError as exc:
        console.err(str(exc))
        return 2

    st: Dict[str, str] = manifest.get(state, {}) or {}
    done = ok = failed = 0
    console.heading(f"{'APPLY' if apply else 'DRY-RUN'}: {header} — {args.schema}")
    try:
        for kind in order:
            for o in manifest["objects"].get(kind, []):
                ident = f"{kind}:{o['name']}"
                sql = o[key]
                if st.get(ident) == "done":
                    continue
                if not apply:
                    console.info(f"  [dry-run] {sql}")
                    continue
                try:
                    target.apply_ddl(sql)
                    st[ident] = "done"
                    ok += 1
                except Exception as exc:  # noqa: BLE001
                    st[ident] = f"error: {exc}"
                    failed += 1
                    console.err(f"  failed {ident}: {exc}")
                done += 1
    finally:
        target.close()

    if apply:
        manifest[state] = st
        cap_path.write_text(json.dumps(manifest, indent=2))
        console.ok(f"{phase}: applied={ok} failed={failed}")
        return 1 if failed else 0
    total = sum(len(manifest["objects"].get(k, [])) for k in order)
    console.ok(f"{phase}: {total} statement(s) would run (dry-run — use --apply)")
    return 0


def _reconcile(args) -> None:
    """After restore --apply, re-introspect and report what is now present."""
    ws = config.workspace_dir(args.project)
    manifest = json.loads((_prep_dir(ws, args.schema) / "capture.json").read_text())
    tschema = manifest["target_schema"]
    try:
        target = _target(args)
    except config.ConfigError:
        return
    try:
        live = target.capture_secondary_objects(tschema)
    finally:
        target.close()
    for kind in _KINDS:
        want = {o["name"] for o in manifest["objects"].get(kind, [])}
        have = {o["name"] for o in live.get(kind, [])}
        missing = sorted(want - have)
        if missing:
            console.warn(f"  {kind}: {len(missing)} not present after restore: "
                         + ", ".join(missing[:8]) + ("…" if len(missing) > 8 else ""))
        else:
            console.ok(f"  {kind}: all {len(want)} present after restore")


def _update_report(project: str, schema: str, tschema: str,
                   counts: Dict[str, int]) -> None:
    body = [
        "### Target preparation — secondary objects (drop before load / recreate after)",
        "",
        f"- Schema `{schema}` (target `{tschema}`): captured "
        f"**{counts['foreign_keys']}** foreign key(s), **{counts['indexes']}** non-unique "
        f"index(es), **{counts['triggers']}** trigger(s) for drop/recreate around the "
        "data load. Primary/unique keys are kept.",
        "",
        "Scripts: `03-validation/target-prep/" + schema.upper() +
        "/{drop-preload,restore-postload}-" + schema.upper() + ".sql`. Run "
        "`pre-load-drop` before loading data and `post-load-restore` afterwards "
        "(dry-run unless `--apply`).",
        "",
    ]
    # order 31: renders just under the Validation (order 30) section header.
    report.update_section(project, "validation.targetprep", 31, "\n".join(body))
