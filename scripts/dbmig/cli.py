"""dbmig command-line interface (argparse).

Usage: ``dbmig [--conn PATH] [--config PATH] <command> [options]`` — via the
console script (``pip install -e scripts/``), the repo-root ``./dbmig`` wrapper,
or ``python -m dbmig`` from ``scripts/``. Every command exits non-zero on
failure. The connections file defaults to ``./connections.yaml`` (override with
``--conn`` or the ``CONN_FILE`` env var); the migration config defaults to
``./migration-config.yaml`` (override with ``--config`` or ``MIGRATION_CONFIG``).
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
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
    parser.add_argument("--conn", default=None, metavar="PATH",
                        help="connections file (default ./connections.yaml; same as "
                             "the CONN_FILE env var, which this flag overrides)")
    parser.add_argument("--config", default=None, metavar="PATH",
                        help="migration config (default ./migration-config.yaml; same "
                             "as the MIGRATION_CONFIG env var, which this flag overrides)")
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
    p.add_argument("--target-schema", dest="target_schema", default=None,
                   help="target schema/database name (default: the DMS SC target schema "
                        "recorded by import-dms-sc, else --schema lower-cased)")
    p.add_argument("--method", choices=["toolkit", "fdw"], default=None,
                   help="data-movement method: 'toolkit' (default) pulls rows through "
                        "this host and COPYs into the target; 'fdw' makes the target "
                        "PostgreSQL read directly from the source via oracle_fdw/tds_fdw "
                        "(cloud-to-cloud, best when the toolkit host is on a slow VPN; "
                        "PostgreSQL target only). Overrides testing.data_method in "
                        "migration-config.")
    p.add_argument("--exclude", default=None,
                   help="comma-separated tables to skip (e.g. ones needing custom "
                        "read-time conversion); applied after --tables")
    p.add_argument("--workers", type=int, default=4,
                   help="max concurrent work units (default 4). Each unit is a table or "
                        "a table's PK shard and opens its own source+target connections")
    p.add_argument("--batch-size", type=int, default=50000,
                   help="rows per COPY batch (default 50000); toolkit method only")
    p.add_argument("--shards", type=int, default=1,
                   help="split each large single-numeric-PK table into N disjoint PK-range "
                        "readers (default 1 = no intra-table split). Lets one big table be "
                        "copied by many parallel streams")
    p.add_argument("--mode-parallel", dest="mode_parallel",
                   choices=["process", "thread"], default="process",
                   help="'process' (default) gives each unit its own core/GIL for real "
                        "parallel throughput; 'thread' is the legacy GIL-bound pool "
                        "(toolkit method only; fdw always uses threads)")
    p.add_argument("--truncate", action="store_true",
                   help="truncate non-resumable target tables before copy")
    p.add_argument("--fdw-keep", dest="fdw_keep", action="store_true",
                   help="(--method fdw) keep the FDW server/user-mapping/foreign-tables "
                        "after the load instead of dropping them. NOTE: the user mapping "
                        "stores the SOURCE credentials on the target — remove them later "
                        "with --fdw-cleanup. Default: drop after load.")
    p.add_argument("--fdw-cleanup", dest="fdw_cleanup", action="store_true",
                   help="(--method fdw) drop the FDW server (CASCADE) and staging schema "
                        "for --schema, then exit without loading (tidy up a --fdw-keep run)")

    # reset-identity
    p = sub.add_parser("reset-identity",
                       help="sync identity/serial/AUTO_INCREMENT counters on the target "
                            "to MAX(key) and verify (dry-run unless --apply)")
    _add_common(p, tables=True)
    p.add_argument("--target-schema", dest="target_schema", default=None,
                   help="target schema/database name (default: the DMS SC target schema "
                        "recorded by import-dms-sc, else --schema lower-cased)")
    p.add_argument("--apply", action="store_true",
                   help="actually sync the counters, then re-verify (default: report only)")

    # compare
    p = sub.add_parser("compare", help="reconcile source vs target row counts")
    _add_common(p, tables=True)
    p.add_argument("--target-schema", dest="target_schema", default=None,
                   help="target schema/database name (default: the DMS SC target schema "
                        "recorded by import-dms-sc, else --schema lower-cased)")
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

    # app-scan (application modernization pre-scan)
    p = sub.add_parser("app-scan",
                       help="read-only pre-scan of an application: dialect SQL sites, routine "
                            "calls, config, entity<->target column type cross-check")
    p.add_argument("--app-dir", dest="app_dir", required=True,
                   help="application root directory")
    p.add_argument("--project", default=None, help="run workspace under migrations/")
    p.add_argument("--target-schema", dest="target_schema", default=None,
                   help="migrated target schema to cross-check entities against "
                        "(default: target default_schema)")
    p.add_argument("--no-target", dest="no_target", action="store_true",
                   help="skip the live target catalog cross-check")

    # status
    p = sub.add_parser("status",
                       help="compact progress per phase + next pending prompt files "
                            "(read this instead of large manifests)")
    _add_common(p)
    p.add_argument("--phase", choices=["schema", "code", "tests"], default=None)
    p.add_argument("--next", type=int, default=3,
                   help="how many pending prompt files to list (default 3)")

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

    _add_gate_parsers(sub)
    return parser


def _add_dir(p: argparse.ArgumentParser) -> None:
    p.add_argument("--project", default=None,
                   help="run workspace name under migrations/ (see other commands)")
    p.add_argument("--dir", default=None, metavar="PATH",
                   help="use this migration folder instead of migrations/<project> "
                        "(e.g. a sample-run-* folder)")


def _add_channel(p: argparse.ArgumentParser) -> None:
    p.add_argument("--approved-by", dest="approved_by", default=None,
                   help="who decided (default: git user.name, else $USER). Recorded, "
                        "not authenticated")
    p.add_argument("--via", choices=["cli", "chat"], default=None,
                   help="channel the decision was given on; an AI assistant passes "
                        "'chat' after the user explicitly approved in the conversation")


def _add_gate_parsers(sub) -> None:
    from .project import ALL_GATED_PHASES, PHASES
    phases = list(ALL_GATED_PHASES)

    g = sub.add_parser("gate", help="phase gate records: status / approve / reject")
    gs = g.add_subparsers(dest="gate_cmd", metavar="<status|approve|reject>")
    gs.required = True
    p = gs.add_parser("status", help="each gate: status (incl. stale), blockers, "
                                     "acknowledgements, changes since approval")
    _add_dir(p)
    p.add_argument("--json", action="store_true")
    p = gs.add_parser("approve", help="record a gate approval (user action)")
    p.add_argument("phase", choices=phases)
    _add_dir(p)
    _add_channel(p)
    p.add_argument("--note", default=None, help="note recorded with the approval")
    p.add_argument("--ack", action="append", default=None, metavar="KIND",
                   help="acknowledge open items of this kind (repeatable)")
    p.add_argument("--ack-all", dest="ack_all", action="store_true",
                   help="acknowledge every open item kind of the phase")
    p = gs.add_parser("reject", help="record a gate rejection (user action)")
    p.add_argument("phase", choices=phases)
    _add_dir(p)
    _add_channel(p)
    p.add_argument("--reason", required=True)

    d = sub.add_parser("decision", help="decision queue: list / raise / answer / withdraw")
    ds = d.add_subparsers(dest="decision_cmd", metavar="<list|raise|answer|withdraw>")
    ds.required = True
    p = ds.add_parser("list", help="list decisions")
    _add_dir(p)
    p.add_argument("--open", action="store_true", help="only open decisions")
    p.add_argument("--phase", default=None)
    p.add_argument("--json", action="store_true")
    p = ds.add_parser("raise", help="record an ambiguity that needs the user's choice")
    _add_dir(p)
    p.add_argument("--phase", required=True, choices=list(PHASES))
    p.add_argument("--kind", required=True, help="e.g. fulltext_redesign, needs_human")
    p.add_argument("--objects", default="", help="comma-separated SCHEMA.NAME objects")
    p.add_argument("--question", default=None, help="required for non-standard kinds")
    p.add_argument("--option", action="append", default=None, metavar="ID=LABEL",
                   help="an option (repeatable; at least two for non-standard kinds)")
    p.add_argument("--recommend", default=None, metavar="ID")
    p.add_argument("--detail", default=None, help="context shown with the question")
    p.add_argument("--raised-by", dest="raised_by", default=None,
                   help="what raised it, e.g. skill:construction")
    p = ds.add_parser("answer", help="record the user's choice")
    p.add_argument("id")
    p.add_argument("--choice", required=True)
    p.add_argument("--rationale", default=None)
    _add_dir(p)
    _add_channel(p)
    p = ds.add_parser("withdraw", help="withdraw an open decision that no longer applies")
    p.add_argument("id")
    p.add_argument("--reason", required=True)
    _add_dir(p)
    _add_channel(p)

    p = sub.add_parser("review", help="build the read-only review site (progress, gates, "
                                      "decisions, code and test browsers, documents)")
    _add_dir(p)
    p.add_argument("--out", default=None, metavar="DIR",
                   help="output folder (default migrations/<project>/review/; a temp folder "
                        "for folders outside migrations/)")
    p.add_argument("--open", action="store_true", help="open it in the browser")
    p.add_argument("--watch", action="store_true", help="rebuild when artifacts change")
    p.add_argument("--serve", action="store_true",
                   help="serve it read-only on 127.0.0.1 with live reload")
    p.add_argument("--port", type=int, default=0, help="port for --serve (default: any free)")

    pr = sub.add_parser("project", help="project.yaml helpers")
    ps = pr.add_subparsers(dest="project_cmd", metavar="<init>")
    ps.required = True
    p = ps.add_parser("init", help="create project.yaml for a new or existing workspace")
    _add_dir(p)

    p = sub.add_parser("app-backup",
                       help="application modernization: back up the application before the "
                            "first edit (git when possible, else a file copy)")
    _add_dir(p)
    p.add_argument("--app", default=None, metavar="DIR", help="application directory")
    p.add_argument("--mode", choices=["auto", "git", "file-copy"], default="auto",
                   help="auto (default): git when the app is in a clean git repo, else file "
                        "copy. git falls back to file copy when git cannot be used")
    p.add_argument("--scope", default="", metavar="PATHS",
                   help="comma-separated in-scope paths relative to the app (default: all)")
    p.add_argument("--force", action="store_true",
                   help="make a new backup even when one is recorded")
    p.add_argument("--json", action="store_true")

    q = sub.add_parser("questionnaire",
                       help="optional markdown intake: new / check (round 1 before the "
                            "inventory, round 2 for the decisions found)")
    qs = q.add_subparsers(dest="q_cmd", metavar="<new|check>")
    qs.required = True
    for name, hlp in (("new", "generate the questionnaire file"),
                      ("check", "validate the answers (and --apply them)")):
        p = qs.add_parser(name, help=hlp)
        p.add_argument("--project", dest="qproject", default=None,
                       help="workspace name (default: 'project:' in migration-config.yaml; "
                            "without one, round 1 is ./questionnaire.md)")
        p.add_argument("--dir", default=None, metavar="PATH", help="migration folder")
        p.add_argument("--round", type=int, choices=[1, 2], default=1)
        p.add_argument("--module", choices=["db", "app"], default="db",
                       help="db (default): the database migration; app: the optional "
                            "application modernization module (one round, needs --project)")
        p.add_argument("--file", default=None, metavar="PATH", help="questionnaire file to use")
        if name == "new":
            p.add_argument("--pair", default=None,
                           help="engine pair, e.g. oracle-to-postgresql (default: from "
                                "connections.yaml when present)")
            p.add_argument("--force", action="store_true",
                           help="replace a file that already has answers")
        else:
            p.add_argument("--apply", action="store_true",
                           help="write migration-config.yaml, connections.yaml (no "
                                "passwords) and project.yaml / answer the decisions")
            p.add_argument("--overwrite", action="store_true",
                           help="replace existing values in migration-config.yaml / "
                                "connections.yaml")
            p.add_argument("--json", action="store_true")


def _dispatch_gates(args):
    cmd = args.command
    if cmd == "gate":
        from .commands import gate
        return {"status": gate.run_status, "approve": gate.run_approve,
                "reject": gate.run_reject}[args.gate_cmd](args)
    if cmd == "decision":
        from .commands import decision
        return {"list": decision.run_list, "raise": decision.run_raise,
                "answer": decision.run_answer,
                "withdraw": decision.run_withdraw}[args.decision_cmd](args)
    if cmd == "project":
        from .commands import gate
        return gate.run_project_init(args)
    if cmd == "questionnaire":
        from .commands import questionnaire
        return {"new": questionnaire.run_new, "check": questionnaire.run_check}[args.q_cmd](args)
    if cmd == "review":
        from .commands import review
        return review.run(args)
    if cmd == "app-backup":
        from .commands import app_backup
        return app_backup.run(args)
    return None


def _gate_precheck(args) -> int:
    """Warn (default) or refuse (run.enforce_gates: true) when a command runs before
    its prerequisite gate is approved."""
    from . import gates
    if args.command not in gates.REQUIRES:
        return 0
    try:
        mig = config.load_migration_config()
    except config.ConfigError:
        mig = {}
    enforce = bool((mig.get("run") or {}).get("enforce_gates", False))
    try:
        msg = gates.precheck(args.command, config.workspace_dir(args.project),
                             enforce=enforce, apply=bool(getattr(args, "apply", False)))
    except Exception as exc:  # noqa: BLE001 - never break a command on a gate read error
        console.warn(f"could not read gate records: {exc}")
        return 0
    if not msg:
        return 0
    if enforce:
        console.err(f"refused: {msg} (run.enforce_gates is true). See ./dbmig gate status")
        return 2
    console.warn(f"{msg} — see ./dbmig gate status")
    return 0


def _dispatch(args) -> int:
    cmd = args.command
    rc = _dispatch_gates(args)
    if rc is not None:
        return rc
    rc = _gate_precheck(args)
    if rc:
        return rc
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
    if cmd == "reset-identity":
        from .commands import reset_identity
        return reset_identity.run(args)
    if cmd == "app-scan":
        from .commands import app_scan
        return app_scan.run(args)
    if cmd == "status":
        from .commands import status
        return status.run(args)
    if cmd == "mark":
        from .commands import mark
        return mark.run(args)
    console.err(f"unknown command: {cmd}")
    return 2


def package_repo_root() -> Optional[Path]:
    """The dbmig-aidlc checkout this package was loaded from (the ancestor of
    this file that holds skills/ + engines/ + scripts/dbmig), or None if the
    package is running outside a checkout (e.g. a non-editable install)."""
    for d in Path(__file__).resolve().parents:
        if (d / "skills").is_dir() and (d / "engines").is_dir() \
                and (d / "scripts" / "dbmig").is_dir():
            return d
    return None


def _check_location() -> int:
    """Guard against running the toolkit from the wrong directory.

    The connections file and migration config default to the CURRENT directory,
    while run artifacts go to <repo>/migrations. From outside the checkout that
    silently splits a run (or fails with a bare 'file not found'). So: if the
    current directory is not inside the checkout and the user did not point at
    a connections file explicitly (--conn / CONN_FILE), stop with the fix.
    An explicit --conn/CONN_FILE is honoured (with a note where artifacts go)."""
    root = package_repo_root()
    if root is None:
        return 0
    cwd = Path.cwd().resolve()
    if cwd == root or root in cwd.parents:
        return 0
    if os.environ.get("CONN_FILE"):
        mig = os.environ.get("DBMIG_MIGRATIONS_DIR") or str(root / "migrations")
        console.warn(f"running outside the dbmig-aidlc folder ({root}); using "
                     f"connections file {os.environ['CONN_FILE']}; run artifacts go "
                     f"to {mig}")
        return 0
    console.err(f"you are in {cwd}, which is outside the dbmig-aidlc folder ({root}).")
    console.err("dbmig reads ./connections.yaml and ./migration-config.yaml from the "
                "current directory, so run it from the repo root:")
    console.err(f'    cd "{root}" && ./dbmig <command>')
    console.err("or point at your connections file explicitly with "
                "--conn <path> (before the command).")
    return 2


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv if argv is not None else sys.argv[1:])
    # --conn / --config are global flags that override the env vars. They are
    # applied via the env so every command (and FDW/process-pool workers, which
    # re-load config in a child process) sees the same paths. Resolved to
    # absolute paths so a worker's cwd cannot change their meaning.
    if getattr(args, "conn", None):
        os.environ["CONN_FILE"] = str(Path(args.conn).expanduser().resolve())
    if getattr(args, "config", None):
        os.environ["MIGRATION_CONFIG"] = str(Path(args.config).expanduser().resolve())
    rc = _check_location()
    if rc:
        return rc
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
        console.err(f"missing dependency: {exc.name}. Install the toolkit into its "
                    "virtual environment (from the repo root): python3 -m venv .venv "
                    "&& .venv/bin/pip install -e scripts/  — then run ./dbmig <command>")
        return 3
    except Exception as exc:  # noqa: BLE001 - top-level safety net
        console.err(f"unexpected error: {exc}")
        return 1
