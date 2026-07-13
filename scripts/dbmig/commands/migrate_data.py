"""``dbmig migrate-data`` — parallel data copy via engine adapters.

- Parallel workers (one per table) via ThreadPoolExecutor; each worker builds its
  own source + target adapter (and thus its own connections).
- Each table is extracted in chunks produced by ``source.chunk_iterator`` (range
  based on a single numeric PK, else one full-table chunk) and ingested via
  ``target.bulk_insert`` (COPY protocol for PostgreSQL, batched INSERT for MySQL).
- Resume support: the exact chunk boundaries produced on the first run are
  fingerprinted (a signature over the ordered ``(sql, params)`` list) and the
  number of *committed* chunks is persisted. A re-run regenerates the chunks and
  compares the signature: if it matches (source unchanged and same ``--batch-size``),
  the already-committed leading chunks are skipped safely; if it differs (the source
  was mutated or ``--batch-size`` changed, so chunk *i* no longer covers the same PK
  range), ordinal skipping would silently drop/duplicate rows, so the table is
  truncated and reloaded from scratch instead. ``--truncate`` always resets first.
- State writes are atomic (temp file + ``os.replace``) so a crash mid-write can never
  leave truncated JSON that would be misread as "nothing done" and re-copy rows.
"""
from __future__ import annotations

import hashlib
import json
import os
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Dict, List, Optional

import yaml

from .. import config, console, engines
from ..connections import load_pair

_print_lock = threading.Lock()


def _state_dir(project: str) -> Path:
    d = config.workspace_dir(project) / "data" / "_state"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _wm_path(project: str, schema: str, table: str) -> Path:
    return _state_dir(project) / f"{schema.upper()}.{table.upper()}.json"


def _chunk_signature(chunks: List[tuple]) -> str:
    """Stable fingerprint of the ordered chunk boundaries.

    Two runs produce the same signature only if ``chunk_iterator`` yields the
    identical ordered ``(sql, params)`` sequence — i.e. the source PK range and
    ``batch_size`` are unchanged. Any drift invalidates ordinal-based resume.
    """
    canon = json.dumps(
        [[sql, sorted((params or {}).items())] for sql, params in chunks],
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
    """Atomically persist resume state (temp file + os.replace)."""
    tmp = path.with_name(path.name + f".tmp.{os.getpid()}.{threading.get_ident()}")
    tmp.write_text(json.dumps(state))
    os.replace(tmp, path)  # atomic rename on POSIX and Windows


def _say(msg: str) -> None:
    with _print_lock:
        console.info(msg)


def _parse_list(val) -> list:
    return [t.strip() for t in (val or "").split(",") if t.strip()]


def _select_tables(all_names, include, exclude) -> list:
    """Filter table names by an optional include list and an optional exclude list
    (both case-insensitive). Include is applied first, then exclude wins on overlap.
    Order follows ``all_names``."""
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


def _copy_one_table(pair, schema: str, table: str, batch_size: int,
                    project: str, truncate: bool, show_progress: bool = False) -> Dict:
    result = {"table": table, "copied": 0, "status": "ok", "error": None}
    source = engines.get_source_engine(pair)
    target = engines.get_target_engine(pair)
    try:
        columns = [c for c, _ in source.table_columns(schema, table)]
        if not columns:
            result["status"] = "skipped"
            result["error"] = "no columns / table not found"
            return result
        tgt_cols = [c.lower() for c in columns]

        # H3: verify the converted target table actually has every source column
        # (by case-folded name) before streaming any data. Conversion is
        # LLM-driven, so columns can legitimately be renamed/dropped/reordered; a
        # mismatch would otherwise surface as a cryptic mid-copy DB error or, worse,
        # silently omit data. Fail loudly and early with the specific columns.
        try:
            actual = set(target.target_columns(schema.lower(), table.lower()))
        except Exception as exc:  # noqa: BLE001
            actual = None  # target introspection unavailable; skip the guard
            _say(f"{schema}.{table}: could not read target columns ({exc}); "
                 "proceeding without alignment check")
        if actual is not None:
            if not actual:
                result["status"] = "error"
                result["error"] = (f"target table {schema.lower()}.{table.lower()} "
                                   "not found (apply-schema before migrate-data)")
                return result
            missing = [c for c in tgt_cols if c not in actual]
            if missing:
                result["status"] = "error"
                result["error"] = (
                    "source->target column mismatch: target is missing "
                    f"column(s) {', '.join(missing)} "
                    f"(source columns: {', '.join(tgt_cols)}; "
                    f"target columns: {', '.join(sorted(actual))})")
                return result

        pk = source.primary_key_columns(schema, table)
        wm = _wm_path(project, schema, table)

        if truncate:
            target.truncate(schema.lower(), table.lower())
            _save_state(wm, {})

        chunks = list(source.chunk_iterator(schema, table, pk, batch_size))
        signature = _chunk_signature(chunks)
        state = _load_state(wm)
        done = 0
        if state and not truncate:
            if state.get("complete") and state.get("signature") == signature:
                result["status"] = "skipped"
                result["copied"] = int(state.get("copied", 0))
                result["error"] = "already loaded (use --truncate to reload)"
                return result
            if state.get("signature") == signature:
                # Boundaries proven identical -> skipping committed chunks is safe.
                done = int(state.get("done_chunks", 0))
            elif state.get("signature"):
                # Boundaries changed (source mutated or --batch-size differs):
                # chunk i no longer covers the same PK range, so ordinal skipping
                # would drop/duplicate rows. Reload cleanly instead.
                _say(f"{schema}.{table}: chunk boundaries changed since last run "
                     "(source mutated or --batch-size differs); truncating and "
                     "reloading to avoid dropped/duplicated rows.")
                target.truncate(schema.lower(), table.lower())
                _save_state(wm, {})
                done = 0

        progress = None
        if show_progress:
            total = None
            try:
                total = next((t["row_count"] for t in source.get_table_list(schema)
                              if t["name"].upper() == table.upper()), None)
            except Exception:
                total = None
            progress = console.Progress(f"{schema}.{table}", total)
        copied = int(state.get("copied", 0)) if done else 0
        for i, (sql, params) in enumerate(chunks):
            if i < done:
                continue  # committed on a previous run (boundaries verified identical)
            # Stream rows (fetch_iter) straight into the bulk loader — the chunk
            # is never fully materialized in memory.
            n = target.bulk_insert(schema.lower(), table.lower(), tgt_cols,
                                    source.fetch_iter(sql, params))
            copied += n
            if progress:
                progress.advance(n)
            _save_state(wm, {"signature": signature, "done_chunks": i + 1,
                             "copied": copied, "complete": (i + 1) == len(chunks)})
        # Mark complete even when every chunk was already done on a prior run.
        _save_state(wm, {"signature": signature, "done_chunks": len(chunks),
                         "copied": copied, "complete": True})
        result["copied"] = copied
        # Advance identity / AUTO_INCREMENT so post-load app inserts don't collide.
        try:
            target.reset_identity(schema.lower(), table.lower())
        except Exception:
            pass
        if progress:
            progress.done_()
        else:
            _say(f"{schema}.{table}: copied {copied:,} rows in "
                 f"{len(chunks)} chunk(s)" + (f" (resumed past {done})" if done else ""))
    except Exception as exc:  # noqa: BLE001
        result["status"] = "error"
        result["error"] = str(exc).strip()
        with _print_lock:
            console.err(f"{schema}.{table}: {result['error']}")
    finally:
        source.close()
        target.close()
    return result


def run(args) -> int:
    try:
        pair = load_pair()
        # Validate engines resolve (and roles) up front.
        engines.get_source_engine(pair)
        engines.get_target_engine(pair)
    except config.ConfigError as exc:
        console.err(str(exc))
        return 2

    include = _parse_list(getattr(args, "tables", None))
    exclude = _parse_list(getattr(args, "exclude", None))

    disco = engines.get_source_engine(pair)
    try:
        names = _select_tables(disco.list_tables(args.schema), include, exclude)
        if exclude:
            console.info(f"excluding {len(exclude)} table(s): {', '.join(exclude)}")
        # Order tables by foreign-key dependency so parents load before children.
        try:
            deps = disco.foreign_key_deps(args.schema, names)
        except Exception as exc:  # noqa: BLE001
            console.warn(f"could not read foreign keys ({exc}); loading in name order")
            deps = {}
    finally:
        disco.close()

    if not names:
        console.warn("no tables to migrate")
        return 0

    from ..engines.base import topological_tiers
    tiers = topological_tiers(names, deps)

    workers = max(1, int(args.workers))
    batch_size = max(1000, int(args.batch_size))
    if workers > 8:
        console.warn(f"--workers {workers} opens up to {workers * 2} concurrent DB "
                     "connections (source + target per worker). Ensure the source "
                     "session limit and target max_connections allow it.")
    console.heading(f"Data migration — {len(names)} table(s), {workers} worker(s)")

    show_progress = workers == 1  # live single-line progress only when serial
    if len(tiers) > 1:
        console.info(f"FK-dependency load order: {len(tiers)} tier(s) "
                     f"(parents before children).")
    results: List[Dict] = []
    # Run one dependency tier at a time; parallelize tables within a tier.
    for ti, tier in enumerate(tiers, start=1):
        if len(tiers) > 1:
            console.info(f"tier {ti}/{len(tiers)}: {', '.join(tier)}")
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = {
                pool.submit(_copy_one_table, pair, args.schema.upper(), name,
                            batch_size, args.project, args.truncate, show_progress): name
                for name in tier
            }
            for fut in as_completed(futures):
                results.append(fut.result())

    total_rows = sum(r["copied"] for r in results)
    errors = [r for r in results if r["status"] == "error"]

    outdir = config.workspace_dir(args.project) / "data"
    outdir.mkdir(parents=True, exist_ok=True)
    (outdir / config.manifest_file("migrate_report", args.schema)).write_text(
        yaml.safe_dump({"total_rows": total_rows, "results": results},
                       sort_keys=False))

    console.heading("Data migration results")
    console.ok(f"copied {total_rows:,} rows across {len(results)} table(s)")
    if errors:
        console.err(f"{len(errors)} table(s) failed:")
        for r in errors[:20]:
            console.err(f"  {r['table']}: {r['error']}")
        return 1
    return 0
