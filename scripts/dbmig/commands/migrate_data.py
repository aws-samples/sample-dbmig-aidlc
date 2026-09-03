"""``dbmig migrate-data`` — parallel data copy via engine adapters.

Throughput design (three levers, all preserving the COPY/executemany fast path):

1. **Process-based parallelism.** Work units run in a ``ProcessPoolExecutor`` so each
   concurrent copy gets its own interpreter/GIL and CPU core (threads share one GIL and
   the per-row COPY marshaling then serializes — the reason a thread pool does not scale).
   ``--mode thread`` keeps the legacy thread pool for environments where spawning is
   undesirable (and for A/B comparison).

2. **Intra-table PK sharding.** A large table with a single numeric primary key is split
   into ``--shards`` disjoint PK ranges, each a separate work unit / process — so a single
   huge table is read by many parallel streams instead of one. Non-shardable tables
   (composite / non-numeric / no PK, or small) stay a single unit.

3. **Read/write pipelining.** Within a unit the source fetch runs on a producer thread
   feeding a bounded row queue while the COPY consumer drains it, so the source read
   round-trips overlap the target write instead of alternating on one thread.

Resume, ``--truncate``, source→target column alignment, and FK-dependency load ordering
(parents before children) are all preserved. Resume state is per (schema, table, shard).
"""
from __future__ import annotations

import hashlib
import json
import os
import queue
import threading
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Dict, List, Optional

import yaml

from .. import config, console, engines
from ..connections import load_pair
from ..engines.base import topological_tiers

# Sentinel + default bound for the read-ahead row queue (pipelining).
_QUEUE_MAXROWS = 20000


# ---- resume state ---------------------------------------------------------

def _state_dir(project: str) -> Path:
    d = config.workspace_dir(project) / "data" / "_state"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _wm_path(project: str, schema: str, table: str, shard: Optional[int]) -> Path:
    suffix = "" if shard is None else f".s{shard:03d}"
    return _state_dir(project) / f"{schema.upper()}.{table.upper()}{suffix}.json"


def _chunk_signature(chunks: List[tuple]) -> str:
    canon = json.dumps([[sql, sorted((p or {}).items())] for sql, p in chunks],
                       sort_keys=True, default=str)
    return hashlib.sha256(canon.encode("utf-8")).hexdigest()


def _load_state(path: Path) -> Dict:
    if path.exists():
        try:
            data = json.loads(path.read_text())
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}
    return {}


def _save_state(path: Path, state: Dict) -> None:
    tmp = path.with_name(path.name + f".tmp.{os.getpid()}.{threading.get_ident()}")
    tmp.write_text(json.dumps(state))
    os.replace(tmp, path)


# ---- read/write pipelining ------------------------------------------------

def _prefetch_rows(row_iter, maxsize: int = _QUEUE_MAXROWS):
    """Yield rows from ``row_iter`` while a producer thread reads AHEAD into a bounded
    queue — so the source fetch overlaps the target COPY instead of alternating on one
    thread. Bounded, so memory stays capped; a producer error is re-raised on the consumer.
    """
    q: "queue.Queue" = queue.Queue(maxsize=maxsize)
    err: list = []
    _END = object()

    def _produce():
        try:
            for row in row_iter:
                q.put(row)
        except BaseException as exc:  # noqa: BLE001 - surfaced on consumer
            err.append(exc)
        finally:
            q.put(_END)

    t = threading.Thread(target=_produce, daemon=True)
    t.start()
    while True:
        item = q.get()
        if item is _END:
            break
        yield item
    if err:
        raise err[0]


# ---- one work unit (table, or a table's PK shard) -------------------------

def _copy_unit(unit: Dict) -> Dict:
    """Copy one work unit (a whole table, or one PK shard of a table).

    Runs in its own process under ProcessPoolExecutor (own GIL/core). Re-loads the
    connection pair from config in the child, chunks its PK range, and streams each
    chunk through the pipelined COPY. Returns a result dict.
    """
    schema = unit["schema"]; table = unit["table"]; shard = unit.get("shard")
    result = {"table": table, "shard": shard, "copied": 0, "status": "ok", "error": None}
    try:
        pair = load_pair()
    except Exception as exc:  # noqa: BLE001
        result["status"] = "error"; result["error"] = f"config: {exc}"
        return result
    source = engines.get_source_engine(pair)
    target = engines.get_target_engine(pair)
    try:
        pk = unit["pk"]
        tgt_cols = unit["tgt_cols"]
        batch_size = unit["batch_size"]
        chunks = list(source.chunk_iterator(schema, table, pk, batch_size,
                                            pk_lo=unit.get("pk_lo"),
                                            pk_hi=unit.get("pk_hi")))
        signature = _chunk_signature(chunks)
        wm = _wm_path(unit["project"], schema, table, shard)
        state = _load_state(wm)
        done = 0
        copied = 0
        if state and state.get("signature") == signature:
            if state.get("complete"):
                result["status"] = "skipped"; result["copied"] = int(state.get("copied", 0))
                return result
            done = int(state.get("done_chunks", 0))
            copied = int(state.get("copied", 0))
        for i, (sql, params) in enumerate(chunks):
            if i < done:
                continue
            rows = _prefetch_rows(source.fetch_iter(sql, params))
            n = target.bulk_insert(schema.lower(), table.lower(), tgt_cols, rows)
            copied += n
            _save_state(wm, {"signature": signature, "done_chunks": i + 1,
                             "copied": copied, "complete": (i + 1) == len(chunks)})
        _save_state(wm, {"signature": signature, "done_chunks": len(chunks),
                         "copied": copied, "complete": True})
        result["copied"] = copied
    except Exception as exc:  # noqa: BLE001
        result["status"] = "error"; result["error"] = str(exc).strip()
    finally:
        source.close(); target.close()
    return result


# ---- planning helpers -----------------------------------------------------

def _parse_list(val) -> list:
    return [t.strip() for t in (val or "").split(",") if t.strip()]


def _select_tables(all_names, include, exclude) -> list:
    inc = {t.upper() for t in (include or [])}
    exc = {t.upper() for t in (exclude or [])}
    out = []
    for n in all_names:
        u = n.upper()
        if inc and u not in inc:
            continue
        if u in exc:
            continue
        out.append(n)
    return out


def _shard_ranges(lo: int, hi: int, shards: int) -> List[tuple]:
    """Split the inclusive PK range [lo, hi] into ``shards`` half-open [a, b) slices."""
    span = hi - lo + 1
    if shards <= 1 or span <= shards:
        return [(lo, hi + 1)]
    step = -(-span // shards)  # ceil
    out = []
    a = lo
    while a <= hi:
        out.append((a, min(a + step, hi + 1)))
        a += step
    return out


def _plan_units(source, target, schema: str, table: str, shards: int, batch_size: int,
                project: str, truncate: bool) -> List[Dict]:
    """Build work units for one table: align columns, (optionally) truncate, and split
    into PK shards when eligible. Returns [] with a raised error handled by the caller."""
    columns = [c for c, _ in source.table_columns(schema, table)]
    tgt_cols = [c.lower() for c in columns]
    # Column-alignment guard (fail fast, like the original single-pass loader).
    try:
        actual = set(target.target_columns(schema.lower(), table.lower()))
    except Exception:
        actual = None
    if actual is not None:
        if not actual:
            raise RuntimeError(f"target table {schema.lower()}.{table.lower()} not found "
                               "(apply-schema before migrate-data)")
        missing = [c for c in tgt_cols if c not in actual]
        if missing:
            raise RuntimeError(f"source->target column mismatch on {table}: target missing "
                               f"{', '.join(missing)}")
    pk = source.primary_key_columns(schema, table)

    if truncate:
        target.truncate(schema.lower(), table.lower())
        for f in _state_dir(project).glob(f"{schema.upper()}.{table.upper()}*.json"):
            try:
                f.unlink()
            except Exception:
                pass

    base = {"schema": schema, "table": table, "pk": pk, "tgt_cols": tgt_cols,
            "batch_size": batch_size, "project": project}
    bounds = source.numeric_pk_bounds(schema, table, pk[0]) if (shards > 1 and len(pk) == 1) else None
    if bounds is not None:
        lo, hi = bounds
        ranges = _shard_ranges(lo, hi, shards)
        if len(ranges) > 1:
            return [dict(base, shard=i, pk_lo=a, pk_hi=b) for i, (a, b) in enumerate(ranges)]
    return [dict(base, shard=None)]


# ---- command --------------------------------------------------------------

def run(args) -> int:
    try:
        pair = load_pair()
        engines.get_source_engine(pair)
        engines.get_target_engine(pair)
    except config.ConfigError as exc:
        console.err(str(exc))
        return 2

    include = _parse_list(getattr(args, "tables", None))
    exclude = _parse_list(getattr(args, "exclude", None))
    workers = max(1, int(args.workers))
    batch_size = max(1000, int(args.batch_size))
    shards = max(1, int(getattr(args, "shards", 1) or 1))
    mode = getattr(args, "mode_parallel", None) or "process"
    truncate = bool(getattr(args, "truncate", False))

    disco = engines.get_source_engine(pair)
    tgt = engines.get_target_engine(pair)
    try:
        names = _select_tables(disco.list_tables(args.schema), include, exclude)
        if not names:
            console.warn("no tables to migrate")
            return 0
        try:
            deps = disco.foreign_key_deps(args.schema, names)
        except Exception as exc:  # noqa: BLE001
            console.warn(f"could not read foreign keys ({exc}); loading in name order")
            deps = {}
        tiers = topological_tiers(names, deps)
        # Plan units per table now (truncate + shard planning use the parent connections).
        units_by_tier: List[List[Dict]] = []
        for tier in tiers:
            tier_units: List[Dict] = []
            for table in tier:
                tier_units.extend(_plan_units(disco, tgt, args.schema.upper(), table,
                                              shards, batch_size, args.project, truncate))
            units_by_tier.append(tier_units)
    finally:
        disco.close(); tgt.close()

    total_units = sum(len(u) for u in units_by_tier)
    console.heading(f"Data migration — {len(names)} table(s), {total_units} unit(s), "
                    f"{workers} {mode} worker(s), shards={shards}")
    if workers > 8:
        console.warn(f"{workers} workers open up to {workers * 2} DB connections "
                     "(source+target per worker); ensure both DBs allow it.")

    Executor = ProcessPoolExecutor if mode == "process" else ThreadPoolExecutor
    results: List[Dict] = []
    for ti, tier_units in enumerate(units_by_tier, start=1):
        if len(units_by_tier) > 1:
            console.info(f"tier {ti}/{len(units_by_tier)}: {len(tier_units)} unit(s)")
        with Executor(max_workers=workers) as pool:
            futures = {pool.submit(_copy_unit, u): u for u in tier_units}
            for fut in as_completed(futures):
                results.append(fut.result())

    # Aggregate per table (sum shards).
    per_table: Dict[str, Dict] = {}
    for r in results:
        t = per_table.setdefault(r["table"], {"copied": 0, "status": "ok", "error": None})
        t["copied"] += r["copied"]
        if r["status"] == "error":
            t["status"] = "error"; t["error"] = t["error"] or r["error"]

    total_rows = sum(t["copied"] for t in per_table.values())
    new_rows = sum(r["copied"] for r in results if r["status"] == "ok")
    skipped_units = sum(1 for r in results if r["status"] == "skipped")
    errors = [(name, t) for name, t in per_table.items() if t["status"] == "error"]

    # Advance identity / AUTO_INCREMENT on the fully-loaded tables so post-load app
    # inserts don't collide (best-effort; done once per table in the parent).
    ok_tables = [name for name, t in per_table.items() if t["status"] == "ok"]
    if ok_tables:
        rid = engines.get_target_engine(pair)
        try:
            for name in ok_tables:
                try:
                    rid.reset_identity(args.schema.lower(), name.lower())
                except Exception:
                    pass
        finally:
            rid.close()

    outdir = config.workspace_dir(args.project) / "data"
    outdir.mkdir(parents=True, exist_ok=True)
    (outdir / config.manifest_file("migrate_report", args.schema)).write_text(
        yaml.safe_dump({"total_rows": total_rows, "tables": per_table,
                        "units": results}, sort_keys=False))

    console.heading("Data migration results")
    console.ok(f"copied {new_rows:,} new row(s) across {len(per_table)} table(s) "
               f"in {total_units} unit(s)"
               + (f"; {skipped_units} unit(s) already loaded (resumed)" if skipped_units else ""))
    if errors:
        console.err(f"{len(errors)} table(s) failed:")
        for name, t in errors[:20]:
            console.err(f"  {name}: {t['error']}")
        return 1
    return 0
