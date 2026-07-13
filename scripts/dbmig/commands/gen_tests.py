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
        # Sample real data from a bounded set of in-scope tables for grounding.
        tables = source.list_tables(args.schema)[:8]
        sample: Dict[str, tuple] = {}
        for t in tables:
            cols, rows = source.sample_rows(args.schema, t, n=3)
            if cols:
                sample[t] = (cols, rows)

        root = config.find_repo_root()
        ws = config.workspace_dir(args.project) / "03-validation"
        prompts_dir = ws / "test_prompts" / args.schema.upper()
        tests_dir = ws / "tests" / args.schema.upper()
        prompts_dir.mkdir(parents=True, exist_ok=True)
        tests_dir.mkdir(parents=True, exist_ok=True)

        units: List[dict] = []
        txn_managed: List[str] = []
        for obj_type, name in callables:
            src = source.code_object_ddl(args.schema, obj_type, name)
            if not src.strip():
                continue
            base = f"{_safe(obj_type)}__{_safe(name)}"
            prompt = prompt_builder.build_test_prompt(
                obj_type, args.schema.upper(), name, src, sample, repo_root=root)
            out = f"tests/{args.schema.upper()}/{base}.test.yaml"
            # Detect procedures that manage their own transactions — not safely
            # net-effect testable via the rollback harness.
            self_txn = obj_type.upper().startswith(("PROC", "PACKAGE")) and \
                self_manages_transaction(src)
            caution = ""
            if self_txn:
                txn_managed.append(f"{obj_type} {name}")
                caution = (
                    "<!-- CAUTION: this object manages its own transaction "
                    "(COMMIT/ROLLBACK/BEGIN TRAN). It is NOT safely net-effect "
                    "testable via the rollback harness — an internal COMMIT persists "
                    "to the source and an internal ROLLBACK unbalances the harness "
                    "transaction. Write a NON-DESTRUCTIVE case (e.g. target a "
                    "non-existent key) or leave 'cases: []' and note it. -->\n")
            header = (
                f"<!-- dbmig test-generation prompt\n"
                f"     object: {obj_type} {args.schema.upper()}.{name}\n"
                f"     Write the test spec (YAML) to: {out}\n"
                f"     Then set status 'generated' in "
                f"{config.manifest_file('test-manifest', args.schema)}. -->\n"
                f"{caution}\n")
            (prompts_dir / f"{base}.prompt.md").write_text(header + prompt)
            unit = {
                "name": name,
                "object_type": obj_type,
                "schema": args.schema.upper(),
                "prompt_file": str((prompts_dir / f"{base}.prompt.md").relative_to(ws)),
                "spec_file": out,
                "status": "pending",
            }
            if self_txn:
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
    console.ok(f"{len(units)} callable(s); sampled {len(sample)} table(s) of real data")
    console.ok(f"Prompt bundles: {prompts_dir}")
    console.ok(f"Manifest:       {manifest_path}")
    if txn_managed:
        console.warn(
            f"{len(txn_managed)} object(s) manage their own transaction and are not "
            "safely net-effect testable via the rollback harness (flagged "
            "test_mode: manual): " + ", ".join(txn_managed))
    try:
        client.convert("")
    except HandoffRequired:
        console.info(
            "Provider 'kiro': Kiro now generates a test spec (.test.yaml) per object "
            "from its prompt bundle (using the sampled real data), writes it to the "
            "spec_file, and sets status 'generated'. Then run: dbmig run-tests "
            f"--schema {args.schema} --project {args.project}")
    return 0
