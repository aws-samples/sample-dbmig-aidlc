"""``dbmig gen-tests`` — prepare equivalence-test generation (LLM = Kiro).

Extracts testable callables (functions, procedures, packages), samples REAL rows
from the source so tests use values that actually exist, and writes a prompt
bundle per object. Kiro (db-migration-validation skill) then writes a test spec
(``.test.yaml``) per object; ``dbmig run-tests`` executes them.
"""
from __future__ import annotations

import datetime as _dt
import re
from typing import Dict, List

from .. import config, console, engines
from ..connections import load_pair
from ..conversion import prompt_builder
from ..conversion.llm_client import make_client, HandoffRequired
from ..manifest import write_manifest


def _now() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _safe(name: str) -> str:
    return name.lower().replace(" ", "_")


# Procedures that manage their own transactions can't be net-effect tested by the
# run-tests harness (which wraps each case in a transaction and rolls it back): an
# internal COMMIT persists to the source, and an internal ROLLBACK unbalances the
# harness transaction (e.g. SQL Server error 266). Flag them for manual review.
_TXN_RE = re.compile(
    r"\b(COMMIT|ROLLBACK|SAVE\s+TRAN(?:SACTION)?|BEGIN\s+TRAN(?:SACTION)?)\b",
    re.IGNORECASE)


def self_manages_transaction(sql: str) -> bool:
    """True if stored-code text contains explicit transaction control."""
    if not sql:
        return False
    # ignore line/block comments so a commented-out COMMIT doesn't trip detection
    stripped = re.sub(r"--[^\n]*", "", sql)
    stripped = re.sub(r"/\*.*?\*/", "", stripped, flags=re.DOTALL)
    return bool(_TXN_RE.search(stripped))


# Data-coverage levels written per test unit (consumed by run-tests).
LOW_COVERAGE = "LOW_COVERAGE"     # every referenced table is empty
PARTIAL_COVERAGE = "PARTIAL"      # some referenced tables are empty
FULL_COVERAGE = "OK"              # every referenced table has rows
NO_TABLES = "n/a"                 # no schema table referenced (pure computation)


def referenced_tables(sql: str, tables) -> list:
    """Schema tables whose name appears as a whole word in ``sql`` (comments
    stripped). Heuristic, catalog-grounded: only names that really exist in the
    schema can match, so it never invents a dependency."""
    if not sql:
        return []
    body = re.sub(r"--[^\n]*", "", sql)
    body = re.sub(r"/\*.*?\*/", "", body, flags=re.DOTALL)
    # One pass over the source's identifiers, then a set lookup per table —
    # O(len(sql) + tables) instead of one regex per table (1000s of tables x
    # 1000s of objects on large schemas).
    words = {w.upper() for w in re.findall(r"[A-Za-z_][A-Za-z0-9_$#]*", body)}
    # A table named like an SQL keyword (Order, User, Group …) is only a reference when used
    # as an identifier: qualified (dbo.Order), bracketed ([Order]) or quoted ("Order") —
    # otherwise every ORDER BY would "reference" it.
    idents = {m.upper() for m in re.findall(
        r"(?:\.|\[|\")\s*([A-Za-z_][A-Za-z0-9_$#]*)|([A-Za-z_][A-Za-z0-9_$#]*)\s*(?:\]|\")", body)
        for m in m if m}
    return [t for t in tables if t.upper() in words
            and (t.upper() not in _SQL_KEYWORDS or t.upper() in idents)]


_SQL_KEYWORDS = frozenset("""ORDER GROUP USER TABLE SELECT FROM WHERE INDEX KEY VALUES
    DATE TIME TIMESTAMP LEVEL NAME TYPE STATUS SESSION ROLE COMMENT OPTION VIEW SCHEMA
    EVENT OBJECT FILE ROWS ROW SET CASE CHECK COLUMN TRANSACTION""".split())


def coverage_level(row_counts: Dict[str, int]) -> str:
    """Classify an object's data coverage from its referenced tables' row counts
    (a negative count = unknown and is not treated as empty)."""
    if not row_counts:
        return NO_TABLES
    empty = [t for t, n in row_counts.items() if n == 0]
    if len(empty) == len(row_counts):
        return LOW_COVERAGE
    return PARTIAL_COVERAGE if empty else FULL_COVERAGE


_TARGET_CODE_LIMIT = 16000   # chars; a huge package is summarised by the assistant


def converted_code_index(workspace, schema) -> Dict[tuple, str]:
    """{(OBJECT_TYPE, NAME): converted target code} from the construction phase's
    code manifest, for units whose output file exists. Lets test prompts use the
    real target names/signatures (flattened package routines, changed argument
    lists) instead of guessing them. A PACKAGE BODY output is folded into its
    PACKAGE entry."""
    import yaml as _yaml
    ws = workspace / "02-construction"
    path = config.resolve_manifest(ws, "code-manifest", schema)
    if not path.exists():
        return {}
    try:
        units = (_yaml.safe_load(path.read_text()) or {}).get("units") or []
    except Exception:  # noqa: BLE001
        return {}
    out: Dict[tuple, str] = {}
    for u in units:
        f = ws / str(u.get("output_file", ""))
        if not u.get("output_file") or not f.is_file():
            continue
        otype = str(u.get("object_type", "")).upper().replace(" BODY", "")
        key = (otype, str(u.get("name", "")).upper())
        text = f.read_text()
        out[key] = (out.get(key, "") + "\n" + text).strip()
    for k, v in out.items():
        if len(v) > _TARGET_CODE_LIMIT:
            out[k] = v[:_TARGET_CODE_LIMIT] + "\n-- … [truncated; full file in 02-construction/code/]"
    return out


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

    sample_n = 5
    mig = config.load_migration_config()
    try:
        sample_n = int(((mig.get("testing") or {}).get("sample_rows_per_table")) or 5)
    except Exception:
        sample_n = 5

    console.info(f"Extracting callables + sampling real data for {args.schema} ...")
    try:
        callables = source.list_callables(args.schema)
        if not callables:
            console.warn("no functions/procedures/packages found")
            return 0
        # Real data is sampled lazily, only for tables some object actually reads
        # (large schemas: never sample thousands of unrelated tables).
        all_tables = source.list_tables(args.schema)
        sample: Dict[str, tuple] = {}

        def _sample(t: str) -> None:
            if t in sample:
                return
            cols, rows = source.sample_rows(args.schema, t, n=3)
            if cols:
                sample[t] = (cols, rows)

        row_counts: Dict[str, int] = {}

        def _rows(t: str) -> int:
            if t not in row_counts:
                try:
                    row_counts[t] = int(source.count_rows(args.schema, t))
                except Exception:  # noqa: BLE001
                    row_counts[t] = -1
            return row_counts[t]

        root = config.find_repo_root()
        ws = config.workspace_dir(args.project) / "03-validation"
        prompts_dir = ws / "test_prompts" / args.schema.upper()
        tests_dir = ws / "tests" / args.schema.upper()
        prompts_dir.mkdir(parents=True, exist_ok=True)
        tests_dir.mkdir(parents=True, exist_ok=True)

        shared = prompt_builder.write_shared_context(ws, prompt_builder.TESTS, root)
        source_note = source.legacy_syntax_note()
        if source_note:
            console.warn(f"legacy source (major version {source.major_version()}): "
                         "test prompts restrict source SQL to that version's syntax")
        converted = converted_code_index(config.workspace_dir(args.project),
                                         args.schema)
        units: List[dict] = []
        pending: List[dict] = []          # per-object analysis, batched below
        txn_managed: List[str] = []
        low_cov: List[str] = []
        for obj_type, name in callables:
            src = source.code_object_ddl(args.schema, obj_type, name)
            if not src.strip():
                continue
            base = f"{_safe(obj_type)}__{_safe(name)}"
            # Data coverage: which schema tables does this object read, and do they
            # hold any rows? Only non-empty referenced tables are sampled.
            refs = referenced_tables(src, all_tables)
            ref_counts = {t: _rows(t) for t in refs}
            level = coverage_level(ref_counts)
            for t in refs:
                if ref_counts[t] != 0:
                    _sample(t)
            out = f"tests/{args.schema.upper()}/{base}.test.yaml"
            # Procedures that manage their own transactions are not safely
            # net-effect testable via the rollback harness.
            self_txn = obj_type.upper().startswith(("PROC", "PACKAGE")) and \
                self_manages_transaction(src)
            notes = []
            if self_txn:
                txn_managed.append(f"{obj_type} {name}")
                notes.append(
                    f"CAUTION {name}: manages its own transaction (COMMIT/ROLLBACK/BEGIN "
                    "TRAN) — NOT safely net-effect testable via the rollback harness. "
                    "Write a NON-DESTRUCTIVE case (e.g. a non-existent key) or leave "
                    "'cases: []' and note it.")
            if level == LOW_COVERAGE:
                low_cov.append(f"{obj_type} {name}")
                notes.append(
                    f"LOW_COVERAGE {name}: every table it reads is EMPTY in the source "
                    f"({', '.join(refs)}) — cases only exercise the empty/default path; "
                    "state this in `notes:`.")
            elif level == PARTIAL_COVERAGE:
                notes.append(f"PARTIAL coverage {name}: empty referenced tables: " +
                             ", ".join(t for t, n in ref_counts.items() if n == 0))
            pending.append({"obj_type": obj_type, "name": name, "source_ddl": src,
                            "base": base, "out": out, "refs": refs, "level": level,
                            "ref_counts": ref_counts, "self_txn": self_txn,
                            "notes": notes,
                            "target_code": converted.get((obj_type.upper(),
                                                          name.upper()))})

        from ..engines.base import batch_by_size
        llm = config.llm_config()
        batches = batch_by_size(
            pending, lambda o: len(o["source_ddl"]) + len(o["target_code"] or ""),
            max_items=int(llm.get("test_batch_max_units", 6)),
            max_bytes=int(llm.get("test_batch_max_bytes", 12000)))
        for i, batch in enumerate(batches, start=1):
            tabs = []
            for o in batch:
                tabs += [t for t in o["refs"] if t in sample and t not in tabs]
            prompt = prompt_builder.build_test_batch_prompt(
                batch, args.schema.upper(), {t: sample[t] for t in tabs},
                repo_root=root, shared_context=shared, source_note=source_note)
            pname = (f"{batch[0]['base']}.prompt.md" if len(batch) == 1
                     else f"batch_{i:04d}.prompt.md")
            notes = [n for o in batch for n in o["notes"]]
            header = (
                f"<!-- dbmig test-generation prompt  batch {i}/{len(batches)}\n"
                f"     Write one test spec (YAML) per object:\n"
                + "".join(f"       - {o['obj_type']} {args.schema.upper()}.{o['name']}"  # nosemgrep: string-concat-in-list -- intentional: one long message split across lines
                          f" -> {o['out']}\n" for o in batch)
                + f"     Then set each unit's status 'generated' in "
                f"{config.manifest_file('test-manifest', args.schema)}. -->\n"
                + "".join(f"<!-- {n} -->\n" for n in notes) + "\n")
            (prompts_dir / pname).write_text(header + prompt)
            for o in batch:
                unit = {
                    "name": o["name"],
                    "object_type": o["obj_type"],
                    "schema": args.schema.upper(),
                    "batch_id": i,
                    "prompt_file": str((prompts_dir / pname).relative_to(ws)),
                    "spec_file": o["out"],
                    "status": "pending",
                    "data_coverage": {"level": o["level"],
                                      "tables": dict(o["ref_counts"])},
                }
                if o["self_txn"]:
                    unit["transaction_managed"] = True
                    unit["test_mode"] = "manual"
                units.append(unit)
    finally:
        source.close()

    manifest = {
        "project": args.project,
        "schema": args.schema.upper(),
        "phase": "validation-tests",
        "generated_at": _now(),
        "provider": client.provider,
        "unit_count": len(units),
        "units": units,
    }
    manifest_path = config.resolve_manifest(ws, "test-manifest", args.schema, for_write=True)
    write_manifest(manifest_path, manifest)

    console.heading("Test generation prepared")
    console.ok(f"{len(units)} callable(s) in {len(set(u['prompt_file'] for u in units))} "
               f"prompt(s); sampled {len(sample)} referenced table(s) of real data")
    console.ok(f"Prompt bundles: {prompts_dir}")
    console.ok(f"Manifest:       {manifest_path}")
    if txn_managed:
        console.warn(
            f"{len(txn_managed)} object(s) manage their own transaction and are not "
            "safely net-effect testable via the rollback harness (flagged "
            "test_mode: manual): " + ", ".join(txn_managed))
    if low_cov:
        console.warn(
            f"{len(low_cov)} object(s) are LOW_COVERAGE — every table they read is "
            "empty in the source, so tests can only exercise the empty/default path: "
            + ", ".join(low_cov))
    try:
        client.convert("")
    except HandoffRequired:
        console.info(
            "Provider 'kiro': Kiro now generates a test spec (.test.yaml) per object "
            "from its prompt bundle (using the sampled real data), writes it to the "
            "spec_file, and sets status 'generated'. Then run: dbmig run-tests "
            f"--schema {args.schema} --project {args.project}")
    return 0
