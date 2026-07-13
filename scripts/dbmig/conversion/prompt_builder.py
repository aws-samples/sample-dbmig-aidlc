"""Assemble conversion prompts with injected skill + engine playbook context.

The Oracle->PostgreSQL knowledge lives in the skills and engine references, not
in code rules. This module loads that content and bakes it into each prompt so
the converting LLM (Kiro) has the patterns it needs in-context.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import List, Optional

import yaml

from .. import config

# The construction skill is shared across engine pairs.
_CONSTRUCTION_SKILL = "skills/db-migration-construction/SKILL.md"

# Column names whose sampled values are redacted before entering a prompt bundle
# (prevents secrets/PII in real data from being written to committed files).
#
# Matching is on whole words: a column name is split into tokens on snake_case,
# kebab-case and camelCase boundaries, and a token must MATCH a sensitive term
# exactly (not merely contain it). This keeps genuine secret columns redacted
# (password_hash, PasswordSalt, api_token) while leaving boolean flags and
# metadata columns alone (e.g. credentials_expired, password_changed_at) — those
# hold a flag/timestamp, not a secret.
_SENSITIVE_TOKENS = frozenset({
    "password", "passwd", "pwd", "secret", "token", "salt", "hash",
    "credential", "credentials", "ssn", "cvv",
})
# Multi-word secrets (checked against the delimiter-stripped name).
_SENSITIVE_JOINED = ("apikey", "privatekey", "accesskey", "secretkey")
# When the ONLY non-secret tokens are these flag/metadata words, the column is a
# flag/timestamp (not a stored secret) and is NOT redacted.
_FLAG_TOKENS = frozenset({
    "expired", "expiry", "expires", "locked", "enabled", "disabled",
    "verified", "required", "changed", "updated", "created", "reset",
    "valid", "attempt", "attempts", "count", "flag", "at", "on", "date", "time",
})


def _tokenize_column(name: str) -> List[str]:
    """Split a column name into lowercase word tokens on _/-/space and camelCase."""
    tokens: List[str] = []
    for part in re.split(r"[_\-\s]+", str(name or "")):
        # split camelCase / PascalCase and separate trailing digits
        tokens.extend(re.findall(r"[A-Z]+(?=[A-Z][a-z])|[A-Z]?[a-z]+|[A-Z]+|\d+", part))
    return [t.lower() for t in tokens if t]


def _is_sensitive_column(name: str) -> bool:
    """True if a column name denotes a stored secret/PII value (whole-word match)."""
    tokens = _tokenize_column(name)
    if not tokens:
        return False
    joined = "".join(tokens)
    if any(kw in joined for kw in _SENSITIVE_JOINED):
        return True
    if not any(t in _SENSITIVE_TOKENS for t in tokens):
        return False
    # A secret token is present. If every remaining token is a flag/metadata word,
    # this is a boolean/timestamp column (e.g. credentials_expired) — don't redact.
    non_secret = [t for t in tokens if t not in _SENSITIVE_TOKENS]
    if non_secret and all(t in _FLAG_TOKENS for t in non_secret):
        return False
    return True


def _pair_paths(pair: str) -> dict:
    """Resolve the per-engine-pair asset paths (relative to repo root)."""
    playbook = f"skills/{pair}-playbook/references"
    return {
        "datatype_map": f"engines/{pair}/datatype-map.yaml",
        "playbook": playbook,
        "customer_dir": f"{playbook}/customer-specific",
    }


def _target_engine(pair: str) -> str:
    return pair.split("-to-")[-1] if "-to-" in pair else "postgresql"


def _source_engine(pair: str) -> str:
    return pair.split("-to-")[0] if "-to-" in pair else "oracle"


_DISPLAY = {
    "oracle": "Oracle",
    "mysql": "MySQL",
    "sqlserver": "SQL Server",
    "postgresql": "PostgreSQL",
}


def _source_display(pair: str) -> str:
    return _DISPLAY.get(_source_engine(pair), _source_engine(pair))


def _target_display(target: str) -> str:
    return "MySQL (Aurora MySQL compatible)" if target == "mysql" else \
        "PostgreSQL (Aurora PostgreSQL compatible)"


def _instruction(source_disp: str, target: str, *, code: bool = False) -> str:
    if target == "mysql":
        tdisp = "MySQL (Aurora MySQL)"
        idrule = ("Fold UPPERCASE identifiers to lower_case; MySQL quotes identifiers with "
                  "backticks; a MySQL 'schema' is a database; default storage engine InnoDB.")
    else:
        tdisp = "PostgreSQL"
        idrule = ("Fold UPPERCASE identifiers to lower_case unquoted PostgreSQL identifiers "
                  "unless quoting is required.")
    if code:
        return (f"Convert the following {source_disp} stored code object to {tdisp} "
                f"(procedural SQL — e.g. PL/pgSQL). Return only valid {tdisp}, ready to "
                f"execute. Packages/modules have no direct equivalent: map each routine to "
                f"its own function/procedure. Note any construct that needs human review in "
                f"a SQL comment.")
    return (f"Convert the following {source_disp} object unit to {tdisp} DDL. "
            f"Return only valid {tdisp} DDL, ready to execute. Do not include explanation "
            f"outside SQL comments. Preserve table and column intent; choose appropriate "
            f"{tdisp} types, index types, and constraint forms based on the whole unit. "
            f"{idrule}")


def _read(repo_root: Path, rel: str, limit: Optional[int] = None) -> str:
    path = repo_root / rel
    try:
        text = path.read_text()
    except OSError:
        return ""
    if limit and len(text) > limit:
        text = text[:limit] + "\n... [truncated]\n"
    return text


def _engine_yaml(repo_root: Path, pair: str) -> dict:
    """Load the active pair's engine.yaml (empty dict if unreadable)."""
    path = repo_root / f"engines/{pair}/engine.yaml"
    try:
        return yaml.safe_load(path.read_text()) or {}
    except (OSError, yaml.YAMLError):
        return {}


def _load_context_material(repo_root: Path, pair: str) -> str:
    """Inject the *extra* files listed under ``conversion.context_material`` in
    engine.yaml that ``build_context`` does not already inject directly.

    Previously the ``context_material`` list was decorative — the most valuable
    "learned from a real run" content (``checks/non-portable-constructs.md``) was
    listed but never reached the prompt. This makes engine.yaml authoritative for
    those extra files. The construction skill, datatype map, and playbook
    references are injected separately (structured), so they are skipped here to
    avoid duplication.
    """
    data = _engine_yaml(repo_root, pair)
    items = (data.get("conversion") or {}).get("context_material") or []
    datatype_map = f"engines/{pair}/datatype-map.yaml"
    playbook_dir = f"skills/{pair}-playbook/references"
    parts: List[str] = []
    for raw in items:
        rel = str(raw).strip()
        if not rel or rel.endswith("/"):
            continue  # a directory (e.g. playbook references) — handled elsewhere
        if rel in (_CONSTRUCTION_SKILL, datatype_map) or rel.startswith(playbook_dir):
            continue  # already injected by build_context in structured form
        body = _read(repo_root, rel).strip()
        if body:
            parts.append(f"## {Path(rel).stem}\n\n{body}")
    return "\n\n".join(parts)


def _load_customer_specific(repo_root: Path, customer_dir: str) -> str:
    """Concatenate active customer-specific knowledge files (highest precedence).

    Reads every ``*.md`` in customer-specific/ except the ``_index.md`` guide and
    any ``example-*`` template files. Returns '' if none are present.
    """
    d = repo_root / customer_dir
    if not d.is_dir():
        return ""
    parts: List[str] = []
    for path in sorted(d.glob("*.md")):
        if path.name == "_index.md" or path.name.startswith("example-"):
            continue
        try:
            body = path.read_text().strip()
        except OSError:
            continue
        if body:
            parts.append(f"## {path.stem}\n\n{body}")
    return "\n\n".join(parts)


def build_context(repo_root: Optional[Path] = None, *, for_code: bool = False,
                  pair: Optional[str] = None) -> str:
    """Build the context block injected ahead of the conversion instruction.

    Engine-pair aware: selects the datatype map, playbook references, and
    customer-specific knowledge for the active pair (e.g. oracle-to-postgresql or
    oracle-to-mysql).
    """
    root = repo_root or config.find_repo_root()
    pair = pair or config.active_pair()
    paths = _pair_paths(pair)
    target = _target_engine(pair)
    blocks: List[str] = []

    # Highest precedence: this customer's own environment/application rules.
    customer = _load_customer_specific(root, paths["customer_dir"])
    if customer:
        blocks.append(
            "# CUSTOMER-SPECIFIC KNOWLEDGE — HIGHEST PRECEDENCE\n"
            "These rules describe this customer's environment and application. "
            "They OVERRIDE the general playbook guidance below wherever they "
            "conflict. Apply them first.\n\n" + customer)

    skill = _read(root, _CONSTRUCTION_SKILL)
    if skill:
        blocks.append("# Construction skill guidance\n\n" + skill)

    dtmap = _read(root, paths["datatype_map"])
    if dtmap:
        blocks.append(f"# {_source_display(pair)} -> {target} datatype reference "
                      "(general default)\n\n```yaml\n" + dtmap + "\n```")

    # Extra engine.yaml context_material (e.g. checks/non-portable-constructs.md):
    # the hard-won "learned from a real run" checklists. Injected as authoritative
    # per-pair guidance so they actually reach the conversion prompt.
    checks = _load_context_material(root, pair)
    if checks:
        blocks.append(
            "# Engine-specific conversion checks — non-portable constructs "
            "(learned from real migrations; review before converting)\n\n" + checks)

    # Inject every chapter index for the active pair's playbook as a "what to
    # consult" map (the full topic files remain on disk for Kiro to open).
    idx_text = []
    idx_dir = root / paths["playbook"]
    if idx_dir.is_dir():
        for idx in sorted(idx_dir.glob("*/_index.md")):
            body = idx.read_text() if idx.exists() else ""
            if body:
                idx_text.append(body)
    if idx_text:
        blocks.append(
            "# Playbook topic index — general guidance (open the referenced files "
            f"under `{paths['playbook']}/` as needed; customer-specific rules above "
            "win on conflict)\n\n" + "\n\n".join(idx_text))

    return "\n\n---\n\n".join(blocks)


def build_unit_prompt(units, repo_root: Optional[Path] = None,
                      pair: Optional[str] = None) -> str:
    """Build a conversion prompt for one or more object-units (a batch).

    ``units`` is an ObjectUnit or a list of them.
    """
    if not isinstance(units, (list, tuple)):
        units = [units]
    root = repo_root or config.find_repo_root()
    pair = pair or config.active_pair()
    context = build_context(root, for_code=False, pair=pair)
    src_disp = _source_display(pair)

    sources = []
    for u in units:
        sources.append(
            f"--- SOURCE DDL ({src_disp}) — {u.schema}.{u.name} "
            f"(~{u.num_rows if u.num_rows >= 0 else 'unknown'} rows) ---\n"
            f"{u.source_ddl}")
    source_block = "\n\n".join(sources)

    return (
        f"{context}\n\n"
        f"=== TASK ===\n{_instruction(src_disp, _target_engine(pair), code=False)}\n\n"
        f"{source_block}\n"
    )


def build_code_prompt(code_obj, repo_root: Optional[Path] = None,
                      pair: Optional[str] = None) -> str:
    root = repo_root or config.find_repo_root()
    pair = pair or config.active_pair()
    context = build_context(root, for_code=True, pair=pair)
    return (
        f"{context}\n\n"
        f"=== TASK ===\n{_instruction(_source_display(pair), _target_engine(pair), code=True)}\n\n"
        f"--- SOURCE ({code_obj.object_type}) — {code_obj.schema}.{code_obj.name} ---\n"
        f"{code_obj.source_ddl}\n"
    )


def build_retry_prompt(original_prompt_text: str, previous_ddl: str,
                       error: str, attempt: int, max_retries: int) -> str:
    """Augment the original conversion prompt with the failed DDL + the error.

    Used by the error-retry loop: the original prompt already contains the full
    context (including the target dialect) and the source DDL; here we append the
    previously-generated DDL that failed to apply and the exact target error, and
    ask for a corrected version.
    """
    return (
        original_prompt_text.rstrip()
        + "\n\n"
        f"=== RETRY {attempt}/{max_retries} — PREVIOUS ATTEMPT FAILED ===\n"
        "The DDL you generated previously (below) FAILED to apply to the target "
        "database. Produce a CORRECTED version that runs on the target. Return only "
        "the corrected DDL (fenced or plain), targeting the same object(s). Diagnose "
        "the specific cause shown in the error and fix it (e.g. unsupported function, "
        "type, or syntax; if a feature/extension is unavailable, choose a supported "
        "alternative).\n\n"
        "--- PREVIOUS DDL (failed) ---\n"
        f"{previous_ddl.strip()}\n\n"
        "--- TARGET DATABASE ERROR ---\n"
        f"{error.strip()}\n"
    )


# ---- equivalence test generation -----------------------------------------

_TEST_SPEC_FORMAT = """\
Produce a test specification as YAML with this exact shape, written to the
object's output file. Use ONLY real values taken from the sampled data below so
the tests run against rows that actually exist.

For a FUNCTION (compare the return value for the same inputs on both engines):

    object: <NAME>
    schema: <SCHEMA>
    type: function
    notes: <how inputs were chosen from real data>
    cases:
      - id: c1
        description: <what this case covers>
        source_sql: "SELECT <schema>.<fn>(<real args>) FROM dual"
        target_sql: "SELECT <schema>.<fn>(<real args>)"
        compare: scalar          # scalar | resultset

For a PROCEDURE (no return value — verify the NET EFFECT is identical). YOU decide
which probe queries capture the procedure's effect (the rows/columns/aggregates it
changes); the runner snapshots each probe BEFORE and AFTER the call on each engine
and compares the delta (after - before) across source and target:

    object: <NAME>
    schema: <SCHEMA>
    type: procedure
    notes: <which tables/columns the procedure affects and why these probes verify it>
    cases:
      - id: c1
        description: <what this case covers>
        call_source: "BEGIN <schema>.<proc>(<real args>); END;"
        call_target: "CALL <schema>.<proc>(<real args>)"
        verify:
          - name: <probe name>
            source_sql: "SELECT <agg/col> FROM <schema>.<table> WHERE <real key>"
            target_sql: "SELECT <agg/col> FROM <schema>.<table> WHERE <real key>"

Rules:
- Every test runs inside a transaction that is ROLLED BACK afterward — safe to run.
- Pick a few representative cases (typical, boundary, NULL/edge) using real data.
- Probe queries must be deterministic and return a single scalar each.
- For packages, generate cases for the public subprograms a caller would use.
- Write source_sql / call_source in the SOURCE dialect and target_sql / call_target
  in the TARGET dialect (e.g. Oracle `... FROM dual` / `BEGIN p(); END;`, SQL Server
  `EXEC p ...`, PostgreSQL `SELECT ...` / `CALL p(...)`).
"""


def _format_sample(sample: dict, max_cell: int = 80) -> str:
    """Render sampled real data compactly for the prompt.

    Values are truncated and binary is elided so large/LOB columns (e.g. BLOB
    images) never bloat the prompt — the goal is representative real values, not
    full row contents.
    """
    if not sample:
        return "(no sample data available)"

    def cell(v) -> str:
        if v is None:
            return ""
        if isinstance(v, (bytes, bytearray, memoryview)):
            return f"<binary {len(bytes(v))} bytes>"
        s = str(v)
        if len(s) > max_cell:
            return s[:max_cell] + "…"
        return s

    out = []
    for table, (cols, rows) in sample.items():
        out.append(f"### {table}  (columns: {', '.join(cols)})")
        # Redact values from sensitive-looking columns so secrets/PII (password
        # hashes, salts, tokens, keys) sampled from real data never get written
        # into a prompt bundle that is committed to the repo.
        sensitive = {i for i, c in enumerate(cols) if _is_sensitive_column(c)}
        for r in rows:
            vals = []
            for i, v in enumerate(r):
                if i in sensitive and v not in (None, ""):
                    vals.append("<redacted>")
                else:
                    vals.append(cell(v))
            out.append("  " + " | ".join(vals))
    return "\n".join(out) if out else "(no sample data available)"


def build_test_prompt(obj_type: str, schema: str, name: str, source_ddl: str,
                      sample: dict, repo_root: Optional[Path] = None,
                      pair: Optional[str] = None) -> str:
    """Build a prompt for Kiro to generate an equivalence-test spec (.test.yaml).

    Injects the SQL/PL-SQL playbook + customer-specific context, the object's
    source, and REAL sampled data, then asks for a test spec in the fixed format.
    """
    root = repo_root or config.find_repo_root()
    pair = pair or config.active_pair()
    target = _target_engine(pair)
    context = build_context(root, for_code=True, pair=pair)
    return (
        f"{context}\n\n"
        f"=== TASK — GENERATE EQUIVALENCE TESTS ===\n"
        f"Generate equivalence tests that prove the converted "
        f"{_target_display(target)} {obj_type.lower()} `{schema}.{name}` behaves the "
        f"same as the {_source_display(pair)} source: same input → same return value "
        f"(functions) or same net effect (procedures). Tests will run on BOTH engines "
        f"and the results compared.\n\n"
        f"{_TEST_SPEC_FORMAT}\n\n"
        f"--- SOURCE ({obj_type}) — {schema}.{name} ---\n{source_ddl}\n\n"
        f"--- SAMPLED REAL DATA (use these actual values) ---\n{_format_sample(sample)}\n"
    )
