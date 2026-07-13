"""Shared helpers across target engines."""
from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

ApplySql = Callable[[Any, str], Tuple[bool, Optional[str]]]


def multipass_apply(apply_sql: ApplySql, conn, files: Sequence[Tuple[str, str]],
                    max_passes: int = 5) -> List[Dict[str, Any]]:
    """Apply (label, sql) units, retrying failures across passes.

    Multi-pass resolves ordering dependencies (e.g. a foreign key to a table
    created by a later unit) without parsing the DDL: anything that fails on one
    pass is retried on the next, until a pass makes no further progress.
    Engine-agnostic — ``apply_sql`` does the engine-specific execution.
    """
    pending = list(files)
    results: Dict[str, Dict[str, Any]] = {}
    last_error: Dict[str, Optional[str]] = {}

    for pass_no in range(1, max_passes + 1):
        if not pending:
            break
        still_failing: List[Tuple[str, str]] = []
        progressed = False
        for label, sql in pending:
            ok, error = apply_sql(conn, sql)
            if ok:
                results[label] = {"label": label, "status": "applied",
                                  "error": None, "pass": pass_no}
                progressed = True
            else:
                last_error[label] = error
                still_failing.append((label, sql))
        pending = still_failing
        if not progressed:
            break

    for label, _ in pending:
        results[label] = {"label": label, "status": "failed",
                          "error": last_error.get(label), "pass": max_passes}
    return [results[label] for label, _ in files]


def summarize_cross_schema_deps(rows, schema: str) -> List[Dict[str, Any]]:
    """Group raw dependency edges by the referenced (foreign) schema.

    ``rows`` is an iterable of ``(referencing_object, referenced_schema,
    referenced_object)`` tuples. Edges whose referenced schema is NULL or equal to
    ``schema`` (case-insensitive) are dropped — only *cross-schema* references remain.
    Returns a list (sorted by referenced schema) of
    ``{"referenced_schema": <name>, "edges": ["<obj> -> <schema>.<refobj>", ...]}``.

    Shared by the source adapters (SQL Server, Oracle) so inventory surfaces, up front,
    which other schemas a schema's objects depend on — letting a partial migration see what
    is out of scope (e.g. dbo procs referencing a non-migrated Production schema) instead of
    discovering it only when conversion or runtime fails.
    """
    grouped: "Dict[str, set]" = {}
    schema_l = (schema or "").lower()
    for referencing_obj, ref_schema, ref_obj in rows:
        if not ref_schema or ref_schema.lower() == schema_l:
            continue
        grouped.setdefault(ref_schema, set()).add(
            (referencing_obj or "?", ref_obj or "?"))
    out: List[Dict[str, Any]] = []
    for ref_schema in sorted(grouped):
        edges = sorted(grouped[ref_schema])
        out.append({
            "referenced_schema": ref_schema,
            "edges": [f"{obj} -> {ref_schema}.{ro}" for obj, ro in edges],
        })
    return out
