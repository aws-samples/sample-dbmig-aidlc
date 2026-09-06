"""``dbmig migrate-data --method fdw`` — push-down data load via a PostgreSQL FDW.

The default ``toolkit`` method pulls every row through the host running ``dbmig``
and pushes it back out via ``COPY``. When the source and target are both in the
cloud but the toolkit host is on-premises across a slow VPN, that drags all the
data across the VPN twice. This method instead makes the **target PostgreSQL read
directly from the source** through a foreign data wrapper — ``oracle_fdw`` for
Oracle, ``tds_fdw`` for SQL Server — so the bulk data moves source→target entirely
server-side (cloud-to-cloud) and the toolkit only issues control SQL over the VPN.

PostgreSQL target only (MySQL has no heterogeneous FDW). MySQL targets are guarded
with a clear error; use ``--method toolkit`` or AWS DMS instead.

How it works
------------
1. **Setup (one control connection):** ``CREATE EXTENSION`` the wrapper, then create
   a foreign ``SERVER`` (``dbmig_fdw_srv``) pointing at the source and a
   ``USER MAPPING`` carrying the source credentials.
2. **Staging schema:** foreign tables are created in a dedicated schema
   ``dbmig_fdw_<schema>`` — never the target data schema or ``public`` — so they
   cannot collide with migrated objects. Each foreign table declares the SOURCE
   column names (exact catalog case) with the TARGET column types, so the wrapper
   maps columns by name and values land as the converted schema expects.
3. **Parallel load:** many ``INSERT INTO <target> SELECT FROM <foreign_table>``
   statements run concurrently on independent target connections — one per table,
   or one per PK-range **shard** of a big single-numeric-PK table (``--shards``).
   Each statement is a single server-side stream, so sharding is what parallelizes
   one large table. Threads (not processes) are used because each worker only waits
   on the target while it does the work.
4. **Resume** is per ``(schema, table, shard)``: a completed unit is skipped on a
   re-run; an incomplete shard re-deletes its PK range then re-inserts (idempotent),
   and an incomplete whole-table unit truncates then re-inserts.
5. **Teardown (security):** the ``USER MAPPING`` stores the source credentials on
   the target, so by default the FDW objects (server ``CASCADE`` + staging schema)
   are dropped after the load. ``--fdw-keep`` retains them; ``--fdw-cleanup`` tears
   them down later without loading.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Optional

import yaml

from .. import config, console, engines
from ..connections import load_pair
from ..engines.base import topological_tiers
from ..engines.postgresql import _quote_ident
from .migrate_data import (
    _load_state, _parse_list, _save_state, _select_tables, _shard_ranges,
    _state_dir, _wm_path,
)

# Fixed names for the FDW objects this loader creates. The staging schema is
# per-source-schema so concurrent loads of different schemas don't collide. The
# ``dbmig_fdw_`` prefix is reserved by the toolkit.
FDW_SERVER = "dbmig_fdw_srv"


def _stage_schema(schema: str) -> str:
    return f"dbmig_fdw_{schema.lower()}"


# ---- one work unit (whole table, or one PK shard) -------------------------

def _load_unit(unit: Dict) -> Dict:
    """Run one server-side INSERT ... SELECT (a whole table or one PK shard) on its
    own target connection. Resume-aware and idempotent."""
    schema = unit["schema"]; table = unit["table"]; shard = unit.get("shard")
    result = {"table": table, "shard": shard, "copied": 0, "status": "ok", "error": None}
    lo = unit.get("pk_lo"); hi = unit.get("pk_hi")
    sig = f"{lo}:{hi}:fdw" if shard is not None else "full:fdw"

    wm = _wm_path(unit["project"], schema, table, shard)
    state = _load_state(wm)
    if state.get("signature") == sig and state.get("complete"):
        result["status"] = "skipped"; result["copied"] = int(state.get("copied", 0))
        return result

    try:
        pair = load_pair()
        target = engines.get_target_engine(pair)
    except Exception as exc:  # noqa: BLE001
        result["status"] = "error"; result["error"] = f"config: {exc}"
        return result
    try:
        sch = schema.lower(); tbl = table.lower()
        if shard is not None:
            # Idempotent resume: clear this shard's PK range, then (re)load it. On a
            # first run the range is empty so the DELETE is a no-op. DELETE targets
            # the target table (target PK name); the SELECT filters the foreign
            # table (source PK name).
            target.fdw_delete_range(sch, tbl, unit["pk_target"], lo, hi)
            n = target.fdw_insert_select(sch, tbl, unit["insert_cols"],
                                         unit["stage"], unit["ft"], unit["select_exprs"],
                                         pk=unit["pk_select"], lo=lo, hi=hi)
        else:
            # Whole-table unit: a single atomic INSERT ... SELECT. If it did not
            # complete, nothing was committed, so re-running is safe without a
            # truncate. A clean reload of an already-populated table is requested
            # via --truncate (handled once in the parent, like the toolkit path).
            n = target.fdw_insert_select(sch, tbl, unit["insert_cols"],
                                         unit["stage"], unit["ft"], unit["select_exprs"])
        _save_state(wm, {"signature": sig, "complete": True, "copied": int(n)})
        result["copied"] = int(n)
    except Exception as exc:  # noqa: BLE001
        result["status"] = "error"; result["error"] = str(exc).strip()
    finally:
        target.close()
    return result


# ---- planning -------------------------------------------------------------

def _plan_table(source, target, schema: str, table: str, stage: str, server: str,
                shards: int, project: str, truncate: bool) -> List[Dict]:
    """Create the foreign table for ``table`` and return its work units.

    Columns are aligned SOURCE→TARGET by name (case-insensitive): the foreign table
    declares the exact source column name with the target column's type. A source
    column with no matching target column is a hard mismatch (the target schema was
    not applied, or a column was renamed in conversion) and raises.
    """
    src_cols = source.table_columns(schema.upper(), table)  # [(name, type)] source order
    tgt_types = target.target_column_types(schema.lower(), table.lower())
    if not tgt_types:
        raise RuntimeError(f"target table {schema.lower()}.{table.lower()} not found "
                           "(apply-schema before migrate-data)")
    tmap = {name.lower(): (name, typ) for name, typ in tgt_types}

    foreign_cols: List[tuple] = []   # (source_name, declared_type) — foreign table DDL
    select_exprs: List[str] = []     # SQL over the foreign (source-named) columns
    insert_cols: List[str] = []      # target names — INSERT into target
    missing: List[str] = []
    for src_name, _src_type in src_cols:
        hit = tmap.get(src_name.lower())
        if not hit:
            missing.append(src_name); continue
        tname, ttype = hit
        decl_type, sel_template = source.fdw_column_decl(ttype)
        foreign_cols.append((src_name, decl_type))
        q = _quote_ident(src_name)
        select_exprs.append(sel_template.format(col=q) if sel_template else q)
        insert_cols.append(tname)
    if missing:
        raise RuntimeError(f"source->target column mismatch on {table}: target missing "
                           f"{', '.join(missing)}")

    ft = table.lower()
    target.fdw_create_foreign_table(stage, ft, foreign_cols, server,
                                    source.fdw_foreign_table_options(schema.upper(), table))

    if truncate:
        target.truncate(schema.lower(), ft)
        for f in _state_dir(project).glob(f"{schema.upper()}.{table.upper()}*.json"):
            try:
                f.unlink()
            except Exception:
                pass

    base = {"schema": schema, "table": table, "stage": stage, "ft": ft,
            "insert_cols": insert_cols, "select_exprs": select_exprs, "project": project}

    # Intra-table sharding: one big single-numeric-PK table -> many parallel
    # server-side range scans. The DELETE runs on the TARGET table (target PK
    # name), the INSERT...SELECT WHERE runs on the FOREIGN table (source PK name).
    pk = source.primary_key_columns(schema.upper(), table)
    if shards > 1 and len(pk) == 1:
        bounds = source.numeric_pk_bounds(schema.upper(), table, pk[0])
        if bounds is not None:
            pk_hit = tmap.get(pk[0].lower())
            if pk_hit is not None:
                pk_target = pk_hit[0]      # target column name (DELETE side)
                pk_select = pk[0]          # source/foreign column name (SELECT side)
                lo, hi = bounds
                ranges = _shard_ranges(lo, hi, shards)
                if len(ranges) > 1:
                    return [dict(base, shard=i, pk_target=pk_target,
                                 pk_select=pk_select, pk_lo=a, pk_hi=b)
                            for i, (a, b) in enumerate(ranges)]
    return [dict(base, shard=None)]


# ---- command --------------------------------------------------------------

def run(args) -> int:
    try:
        pair = load_pair()
        source = engines.get_source_engine(pair)
        target = engines.get_target_engine(pair)
    except config.ConfigError as exc:
        console.err(str(exc))
        return 2

    # Guard: FDW push-down needs a PostgreSQL target and an FDW-capable source.
    if not getattr(target, "fdw_capable", False):
        console.err(f"--method fdw requires a PostgreSQL target (got '{target.engine}'). "
                    "MySQL has no heterogeneous FDW — use --method toolkit or AWS DMS.")
        return 2
    wrapper = source.fdw_wrapper()
    if not wrapper:
        console.err(f"source engine '{source.engine}' does not support FDW push-down "
                    "load; use --method toolkit.")
        return 2

    stage = _stage_schema(args.schema)

    # Cleanup-only: tear down the FDW objects and exit (for a prior --fdw-keep run).
    if getattr(args, "fdw_cleanup", False):
        try:
            target.fdw_cleanup(FDW_SERVER, stage)
            console.ok(f"dropped FDW server '{FDW_SERVER}' and staging schema '{stage}'")
            return 0
        except Exception as exc:  # noqa: BLE001
            console.err(f"FDW cleanup failed: {exc}")
            return 1
        finally:
            source.close(); target.close()

    include = _parse_list(getattr(args, "tables", None))
    exclude = _parse_list(getattr(args, "exclude", None))
    workers = max(1, int(args.workers))
    shards = max(1, int(getattr(args, "shards", 1) or 1))
    truncate = bool(getattr(args, "truncate", False))
    keep = bool(getattr(args, "fdw_keep", False))

    units_by_tier: List[List[Dict]] = []
    names: List[str] = []
    try:
        # Setup: extension + server + user mapping + staging schema (one control conn).
        try:
            target.fdw_setup_server(wrapper, FDW_SERVER, source.fdw_server_options(),
                                    source.fdw_user_mapping_options())
        except Exception as exc:  # noqa: BLE001
            console.err(f"could not set up the {wrapper} foreign server: {exc}")
            console.err(f"ensure the '{wrapper}' extension is available on the target "
                        "and the connecting role has rds_superuser.")
            return 1
        target.fdw_create_stage_schema(stage)

        names = _select_tables(source.list_tables(args.schema), include, exclude)
        if not names:
            console.warn("no tables to migrate")
            return 0
        try:
            deps = source.foreign_key_deps(args.schema, names)
        except Exception as exc:  # noqa: BLE001
            console.warn(f"could not read foreign keys ({exc}); loading in name order")
            deps = {}
        tiers = topological_tiers(names, deps)

        plan_errors: List[tuple] = []
        for tier in tiers:
            tier_units: List[Dict] = []
            for table in tier:
                try:
                    tier_units.extend(_plan_table(source, target, args.schema, table,
                                                  stage, FDW_SERVER, shards,
                                                  args.project, truncate))
                except Exception as exc:  # noqa: BLE001
                    plan_errors.append((table, str(exc).strip()))
            units_by_tier.append(tier_units)
    finally:
        source.close(); target.close()

    total_units = sum(len(u) for u in units_by_tier)
    console.heading(f"Data migration (FDW push-down via {wrapper}) — {len(names)} table(s), "
                    f"{total_units} unit(s), {workers} worker(s), shards={shards}")
    console.info("data moves source->target server-side; the toolkit holds only "
                 "target control connections.")
    for table, err in plan_errors:
        console.err(f"skipped {table}: {err}")

    # Run each dependency tier in turn; units within a tier run concurrently.
    results: List[Dict] = []
    for ti, tier_units in enumerate(units_by_tier, start=1):
        if not tier_units:
            continue
        if len([u for u in units_by_tier if u]) > 1:
            console.info(f"tier {ti}/{len(units_by_tier)}: {len(tier_units)} unit(s)")
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = {pool.submit(_load_unit, u): u for u in tier_units}
            for fut in as_completed(futures):
                results.append(fut.result())

    # Aggregate per table (sum shards).
    per_table: Dict[str, Dict] = {}
    for r in results:
        t = per_table.setdefault(r["table"], {"copied": 0, "status": "ok", "error": None})
        t["copied"] += r["copied"]
        if r["status"] == "error":
            t["status"] = "error"; t["error"] = t["error"] or r["error"]
    for table, err in plan_errors:
        per_table[table] = {"copied": 0, "status": "error", "error": err}

    total_rows = sum(t["copied"] for t in per_table.values())
    new_rows = sum(r["copied"] for r in results if r["status"] == "ok")
    skipped_units = sum(1 for r in results if r["status"] == "skipped")
    errors = [(name, t) for name, t in per_table.items() if t["status"] == "error"]

    # Advance identity sequences on fully-loaded tables (best-effort, one control conn).
    ok_tables = [name for name, t in per_table.items() if t["status"] == "ok"]
    rid = engines.get_target_engine(pair)
    try:
        for name in ok_tables:
            try:
                rid.reset_identity(args.schema.lower(), name.lower())
            except Exception:
                pass
        # Teardown unless the user asked to keep the FDW objects.
        if keep:
            console.warn(f"--fdw-keep: leaving FDW server '{FDW_SERVER}' and staging "
                         f"schema '{stage}' in place. The user mapping stores the SOURCE "
                         "credentials on the target — remove them when done with: "
                         f"python -m dbmig migrate-data --schema {args.schema} "
                         f"--project {args.project} --method fdw --fdw-cleanup")
        else:
            try:
                rid.fdw_cleanup(FDW_SERVER, stage)
                console.info(f"dropped FDW server '{FDW_SERVER}' and staging schema "
                             f"'{stage}' (source credentials removed from target)")
            except Exception as exc:  # noqa: BLE001
                console.warn(f"FDW cleanup failed ({exc}); remove manually with "
                             "--method fdw --fdw-cleanup")
    finally:
        rid.close()

    outdir = config.workspace_dir(args.project) / "data"
    outdir.mkdir(parents=True, exist_ok=True)
    (outdir / config.manifest_file("fdw_migrate_report", args.schema)).write_text(
        yaml.safe_dump({"method": "fdw", "wrapper": wrapper, "total_rows": total_rows,
                        "tables": per_table, "units": results}, sort_keys=False))

    console.heading("Data migration results (FDW push-down)")
    console.ok(f"loaded {new_rows:,} new row(s) across {len(ok_tables)} table(s) "
               f"in {total_units} unit(s)"
               + (f"; {skipped_units} unit(s) already loaded (resumed)" if skipped_units else ""))
    if errors:
        console.err(f"{len(errors)} table(s) failed:")
        for name, t in errors[:20]:
            console.err(f"  {name}: {t['error']}")
        return 1
    return 0
