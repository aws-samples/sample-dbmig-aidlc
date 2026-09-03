"""dbmig command-line interface (argparse).

Usage: ``python -m dbmig <command> [options]``. Every command exits non-zero on
failure. The connections file defaults to ``./connections.yaml`` (override with
the ``CONN_FILE`` env var); the migration config defaults to
``./migration-config.yaml`` (override with ``MIGRATION_CONFIG``).
"""
from __future__ import annotations

import argparse
import sys
from typing import List, Optional

from . import __version__, console, config


def _add_common(p: argparse.ArgumentParser, *, schema: bool = True,
                project: bool = True, tables: bool = False) -> None:
    if schema:
        p.add_argument("--schema", required=True, help="source schema/owner (e.g. APP)")
    if project:
        p.add_argument("--project", default=None,
                       help="run workspace name under migrations/ (sanitized to a safe "
                            "folder name). Defaults to 'project:' in migration-config.yaml, "
                            "else 'default'.")
    if tables:
        p.add_argument("--tables", default=None,
                       help="comma-separated table subset (default: all)")


def _add_mode(p: argparse.ArgumentParser) -> None:
    p.add_argument("--mode", choices=["silent", "interactive"], default=None,
                   help="failure handling: silent (default; log to follow-up and "
                        "continue) or interactive (prompt for input/correction). "
                        "Overrides run.mode in migration-config.")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="dbmig",
        description="AI-DLC database migration toolkit. "
                    "Schema conversion is LLM-driven by Kiro; all other steps run "
                    "standalone via Python drivers (oracledb / python-tds / psycopg / "
                    "PyMySQL). Supported pairs: Oracle and SQL Server -> PostgreSQL and MySQL.",
    )
    parser.add_argument("--version", action="version",
                        version=f"dbmig {__version__}")
    sub = parser.add_subparsers(dest="command", metavar="<command>")
    sub.required = True

    # test-connection
    p = sub.add_parser("test-connection", help="verify source/target connectivity")
    p.add_argument("--side", choices=["source", "target", "both"], default="both")

    # inventory
    p = sub.add_parser("inventory", help="assess a source schema; write reports")
    _add_common(p)

    # import-dms-sc
    p = sub.add_parser("import-dms-sc",
                       help="ingest an existing AWS DMS Schema Conversion project "
                            "(local dir) -> manifests + mapping + ACCEPT/VERIFY/MANUAL report")
    p.add_argument("--dms-sc-dir", dest="dms_sc_dir", required=True,
                   help="path to the local DMS SC project directory (the folder "
                        "containing s-*/ t-*/ and action-items/)")
    p.add_argument("--schema", default=None,
                   help="limit to one or more schemas (comma-separated). Default: all "
                        "schemas found in the project.")
    p.add_argument("--project", default=None,
                   help="run workspace name under migrations/ (see other commands)")

    # convert-schema
    p = sub.add_parser("convert-schema",
                       help="extract object-units + build conversion prompts (Kiro converts)")
    _add_common(p, tables=True)

    # convert-code
    p = sub.add_parser("convert-code",
                       help="extract PL/SQL code objects + build prompts (separate pass)")
    _add_common(p)

    # apply-schema
    p = sub.add_parser("apply-schema", help="apply converted DDL to the target")
    _add_common(p, tables=True)
    p.add_argument("--code", action="store_true",
                   help="apply converted code objects (code-manifest) instead of tables")
    p.add_argument("--post-data", dest="post_data", action="store_true",
                   help="apply only the deferred foreign keys + triggers (run AFTER "
                        "migrate-data); the default run applies tables/indexes and "
                        "defers these")
    p.add_argument("--max-retries", type=int, default=None,
                   help="max apply attempts per unit before needs_human "
                        "(default: llm.max_retries in migration-config, or 3)")
    p.add_argument("--dry-run", action="store_true",
                   help="print the DDL that would be applied, without executing it")
    _add_mode(p)

    # gen-tests
    p = sub.add_parser("gen-tests",
                       help="prepare equivalence-test generation from real data (Kiro writes specs)")
    _add_common(p)
    _add_mode(p)

    # run-tests
    p = sub.add_parser("run-tests",
                       help="run equivalence tests (txn + rollback); compare function returns & procedure net-effects")
    _add_common(p)
    _add_mode(p)

    # migrate-data
    p = sub.add_parser("migrate-data", help="parallel data copy with COPY + resume")
    _add_common(p, tables=True)
    p.add_argument("--exclude", default=None,
                   help="comma-separated tables to skip (e.g. ones needing custom "
                        "read-time conversion); applied after --tables")
    p.add_argument("--workers", type=int, default=4,
                   help="max concurrent work units (default 4). Each unit is a table or "
                        "a table's PK shard and opens its own source+target connections")
    p.add_argument("--batch-size", type=int, default=50000,
                   help="rows per COPY batch (default 50000)")
    p.add_argument("--shards", type=int, default=1,
                   help="split each large single-numeric-PK table into N disjoint PK-range "
                        "readers (default 1 = no intra-table split). Lets one big table be "
                        "copied by many parallel streams")
    p.add_argument("--mode-parallel", dest="mode_parallel",
                   choices=["process", "thread"], default="process",
                   help="'process' (default) gives each unit its own core/GIL for real "
                        "parallel throughput; 'thread' is the legacy GIL-bound pool")
    p.add_argument("--truncate", action="store_true",
                   help="truncate non-resumable target tables before copy")

    # compare
    p = sub.add_parser("compare", help="reconcile source vs target row counts")
    _add_common(p, tables=True)
    _add_mode(p)

    # diff-target (reconcile DMS SC import against live target)
    p = sub.add_parser("diff-target",
                       help="reconcile imported DMS SC objects against the LIVE target "
                            "(MATCH/DIFF/MISSING/EXTRA); optionally resolve conflicts")
    _add_common(p)
    p.add_argument("--resolve", choices=["apply-ours", "keep-live", "ask"], default=None,
                   help="act on MISSING/DIFF: apply the DMS SC DDL, keep the live "
                        "version, or ask interactively (default: report only)")
    p.add_argument("--apply", action="store_true",
                   help="actually execute DDL when resolving (default: dry-run print)")

    # capture-target-objects (Phase 3: snapshot secondary objects from the live target)
    p = sub.add_parser("capture-target-objects",
                       help="snapshot live secondary objects (FKs, non-unique indexes, "
                            "triggers) into drop/restore scripts for a data load")
    _add_common(p)

    # pre-load-drop / post-load-restore
    p = sub.add_parser("pre-load-drop",
                       help="drop the captured secondary objects before a data load "
                            "(dry-run unless --apply)")
    _add_common(p)
    p.add_argument("--apply", action="store_true",
                   help="actually execute the drop statements (default: dry-run)")
    p = sub.add_parser("post-load-restore",
                       help="recreate the captured secondary objects after a data load, "
                            "then reconcile (dry-run unless --apply)")
    _add_common(p)
    p.add_argument("--apply", action="store_true",
                   help="actually execute the restore statements (default: dry-run)")

    # verify (DMS SC VERIFY objects)
    p = sub.add_parser("verify",
                       help="list/record verification of DMS SC VERIFY objects "
                            "(so verified work is not repeated)")
    _add_common(p)
    p.add_argument("--set", dest="set", choices=["verified", "pending", "failed"],
                   default=None, help="set verification status (omit to just list)")
    p.add_argument("--objects", default=None,
                   help="comma-separated object names/ids to mark (match by name, "
                        "schema.name, or source id)")
    p.add_argument("--all", action="store_true",
                   help="apply --set to every tracked VERIFY object in the schema")
    p.add_argument("--by", default=None, help="who verified (recorded in the ledger)")
    p.add_argument("--method", default=None,
                   help="verification method, e.g. 'equivalence-test' or 'manual'")
    p.add_argument("--note", default=None, help="free-text note recorded with the verdict")

    # mark
    p = sub.add_parser("mark",
                       help="set manifest unit statuses (helper for the conversion loop)")
    _add_common(p)
    p.add_argument("--status", required=True,
                   choices=["pending", "converted", "applied", "generated", "needs_human"],
                   help="status to set on the units")
    g = p.add_mutually_exclusive_group()
    g.add_argument("--code", action="store_true",
                   help="target the code manifest (code-manifest-<SCHEMA>.yaml)")
    g.add_argument("--tests", action="store_true",
                   help="target the test manifest (test-manifest-<SCHEMA>.yaml)")
    p.add_argument("--tables", dest="only", default=None,
                   help="comma-separated unit names to limit the change to (default: all)")
    p.add_argument("--only-existing-output", action="store_true",
                   help="only mark units whose output_file/spec_file already exists")

    return parser


def _dispatch(args) -> int:
    cmd = args.command
    if cmd == "test-connection":
        from .commands import test_connection
        return test_connection.run(args)
    if cmd == "inventory":
        from .commands import inventory
        return inventory.run(args)
    if cmd == "import-dms-sc":
        from .commands import import_dms_sc
        return import_dms_sc.run(args)
    if cmd == "verify":
        from .commands import verify
        return verify.run(args)
    if cmd == "diff-target":
        from .commands import diff_target
        return diff_target.run(args)
    if cmd == "capture-target-objects":
        from .commands import target_prep
        return target_prep.run_capture(args)
    if cmd == "pre-load-drop":
        from .commands import target_prep
        return target_prep.run_drop(args)
    if cmd == "post-load-restore":
        from .commands import target_prep
        return target_prep.run_restore(args)
    if cmd == "convert-schema":
        from .commands import convert_schema
        return convert_schema.run(args)
    if cmd == "convert-code":
        from .commands import convert_code
        return convert_code.run(args)
    if cmd == "apply-schema":
        from .commands import apply_schema
        return apply_schema.run(args)
    if cmd == "gen-tests":
        from .commands import gen_tests
        return gen_tests.run(args)
    if cmd == "run-tests":
        from .commands import run_tests
        return run_tests.run(args)
    if cmd == "migrate-data":
        from .commands import migrate_data
        return migrate_data.run(args)
    if cmd == "compare":
        from .commands import compare
        return compare.run(args)
    if cmd == "mark":
        from .commands import mark
        return mark.run(args)
    console.err(f"unknown command: {cmd}")
    return 2


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv if argv is not None else sys.argv[1:])
    # Resolve the run workspace name once: CLI --project, else migration-config
    # 'project:', else 'default' — sanitized to a safe folder name.
    if hasattr(args, "project"):
        args.project = config.resolve_project(args.project)
    try:
        return _dispatch(args)
    except KeyboardInterrupt:
        console.err("interrupted")
        return 130
    except ModuleNotFoundError as exc:
        console.err(f"missing dependency: {exc.name}. Install with: "
                    "pip install -r scripts/requirements.txt")
        return 3
    except Exception as exc:  # noqa: BLE001 - top-level safety net
        console.err(f"unexpected error: {exc}")
        return 1
