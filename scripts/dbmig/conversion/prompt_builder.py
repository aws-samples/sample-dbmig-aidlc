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


def _instruction(source_disp: str, target: str, *, code: bool = False,
                 target_schema: Optional[str] = None) -> str:
    if target == "mysql":
        tdisp = "MySQL (Aurora MySQL)"
        idrule = ("Fold UPPERCASE identifiers to lower_case; MySQL quotes identifiers with "
                  "backticks; a MySQL 'schema' is a database; default storage engine InnoDB.")
    else:
        tdisp = "PostgreSQL"
        idrule = ("Fold UPPERCASE identifiers to lower_case unquoted PostgreSQL identifiers "
                  "unless quoting is required.")
    # State the exact target schema so the converter never has to infer it. Inferring
    # it from the connection's database/catalog name is the natural mistake — and wrong:
    # the framework derives the target schema (MySQL: the target DATABASE) from the
    # SOURCE schema name, lower-cased. DDL qualified with anything else applies cleanly
    # into the wrong namespace and only fails later, at the data load.
    qual = ""
    if target_schema:
        noun = "database" if target == "mysql" else "schema"
        qual = (f" Qualify every created object with the target {noun} `{target_schema}` "
                f"(derived from the source schema — do NOT use the connection's "
                f"database/catalog name for qualification).")
    if code:
        return (f"Convert the following {source_disp} stored code object to {tdisp} "
                f"(procedural SQL — e.g. PL/pgSQL). Return only valid {tdisp}, ready to "
                f"execute. Packages/modules have no direct equivalent: map each routine to "
                f"its own function/procedure. Note any construct that needs human review in "
                f"a SQL comment.{qual}")
    return (f"Convert the following {source_disp} object unit to {tdisp} DDL. "
            f"Return only valid {tdisp} DDL, ready to execute. Do not include explanation "
            f"outside SQL comments. Preserve table and column intent; choose appropriate "
            f"{tdisp} types, index types, and constraint forms based on the whole unit. "
            f"{idrule}{qual}")


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


# ---- phase-aware context -------------------------------------------------
#
# Token budget: the context block used to be ~13K tokens and was repeated in EVERY
# prompt (one per table batch, code object and test object — ~95% of all prompt
# bytes in a real run). Two changes keep the guidance while cutting the volume:
#   1. each phase gets only what it needs (tests don't need the datatype map or the
#      playbook; nothing needs the construction SKILL — the assistant already has it
#      loaded; HA/DR, tools, tuning, monitoring chapters never help a conversion);
#   2. the block is written ONCE per run to a shared file (``_context-<phase>.md``)
#      that each prompt references, instead of being inlined N times.

SCHEMA, CODE, TESTS = "schema", "code", "tests"

# Playbook chapters whose topic index is useful for each phase. Chapters not
# listed (ha-dr, tools, performance-tuning, configuration, monitoring, security,
# management, customer-specific/_index guide) are never needed to convert or test
# an object; the files stay on disk for on-demand reading.
_PHASE_CHAPTERS = {
    SCHEMA: {"tables-indexes", "indexes", "physical-storage", "special-features",
             "ansi-sql", "quick-tips", "deprecated-features"},
    CODE: {"sql-plsql", "tsql", "ansi-sql", "special-features", "quick-tips",
           "deprecated-features"},
    TESTS: set(),
}
# engines/<pair>/checks/* files routed per phase (by stem).
_TEST_CHECKS = {"equivalence-spec", "package-naming"}


def _phase_of(phase: Optional[str], for_code: bool) -> str:
    return phase or (CODE if for_code else SCHEMA)


def build_context(repo_root: Optional[Path] = None, *, for_code: bool = False,
                  pair: Optional[str] = None, phase: Optional[str] = None) -> str:
    """Build the context block for one phase (``schema`` | ``code`` | ``tests``).

    Engine-pair aware: selects the datatype map, checks, playbook indexes and
    customer-specific knowledge for the active pair. Customer-specific rules are
    always included (highest precedence).
    """
    root = repo_root or config.find_repo_root()
    pair = pair or config.active_pair()
    phase = _phase_of(phase, for_code)
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

    if phase == TESTS:
        blocks.append("# Equivalence test spec format (applies to every test prompt)\n\n"
                      + _TEST_SPEC_FORMAT)
        tests_checks = []
        for stem in sorted(_TEST_CHECKS):
            body = _read(root, f"engines/{pair}/checks/{stem}.md").strip()
            if body:
                tests_checks.append(f"## {stem}\n\n{body}")
        if tests_checks:
            blocks.append("# Semantic differences to test for (engine checks)\n\n"
                          + "\n\n".join(tests_checks))
        return "\n\n---\n\n".join(blocks)

    dtmap = _read(root, paths["datatype_map"])
    if dtmap:
        blocks.append(f"# {_source_display(pair)} -> {target} datatype reference "
                      "(general default)\n\n```yaml\n" + dtmap + "\n```")

    # Extra engine.yaml context_material (e.g. checks/non-portable-constructs.md):
    # the hard-won "learned from a real run" checklists.
    checks = _load_context_material(root, pair)
    if checks:
        blocks.append(
            "# Engine-specific conversion checks — non-portable constructs "
            "(learned from real migrations; review before converting)\n\n" + checks)

    # Topic indexes for the chapters relevant to this phase only.
    idx_text = []
    idx_dir = root / paths["playbook"]
    if idx_dir.is_dir():
        for idx in sorted(idx_dir.glob("*/_index.md")):
            if idx.parent.name not in _PHASE_CHAPTERS[phase]:
                continue
            body = idx.read_text() if idx.exists() else ""
            if body:
                idx_text.append(body)
    if idx_text:
        blocks.append(
            "# Playbook topic index — general guidance (open the referenced files "
            f"under `{paths['playbook']}/` as needed; customer-specific rules above "
            "win on conflict)\n\n" + "\n\n".join(idx_text))

    return "\n\n---\n\n".join(blocks)


def shared_context_name(phase: str) -> str:
    return f"_context-{phase}.md"


def write_shared_context(ws: Path, phase: str, repo_root: Optional[Path] = None,
                         pair: Optional[str] = None) -> str:
    """Write the phase context ONCE into ``ws`` and return its file name.

    Each prompt then carries a one-line reference instead of the full block.
    Returns the path relative to the run workspace (e.g. ``02-construction/_context-code.md``)."""
    body = build_context(repo_root, pair=pair, phase=phase)
    ws.mkdir(parents=True, exist_ok=True)
    name = shared_context_name(phase)
    (ws / name).write_text(
        f"<!-- dbmig shared {phase} context — read ONCE per session; every "
        f"{phase} prompt in this run relies on it. Regenerated by each "
        f"{'gen-tests' if phase == TESTS else 'convert-' + phase} run. -->\n\n{body}\n")
    return f"{ws.name}/{name}"   # relative to the run workspace migrations/<project>/


def _context_or_ref(shared: Optional[str], root, pair, phase) -> str:
    if shared:
        return (f"=== CONTEXT ===\nShared {phase} context for this run: "
                f"`migrations/<project>/{shared}`. Read it once "
                "per session if you have not already — it holds the customer-specific "
                "rules (highest precedence), datatype map, engine checks and playbook "
                "index this task relies on. Do not skip it.")
    return build_context(root, pair=pair, phase=phase)


# ---- construct detection (points attention at the relevant guidance) --------

# (regex, hint) per source engine. The hint names the guidance to apply; the full
# rules are in the shared context / playbook. Keeps prompts small but targeted.
_CONSTRUCT_HINTS = {
    "oracle": [
        (r"\bPIPELINED\b|\bPIPE\s+ROW\b", "PIPELINED table function → RETURNS TABLE/SETOF; declared column types must match the query's actual types (checked only at execution)"),
        (r"\bCONNECT\s+BY\b", "hierarchical query → recursive CTE"),
        (r"\bROWNUM\b", "ROWNUM applies BEFORE ORDER BY — reconstruct intent (LIMIT applies after)"),
        (r"CTXSYS|\bCONTAINS\s*\(|\bSCORE\s*\(", "Oracle Text → tsvector/GIN redesign (decision item); do not create DR$ tables"),
        (r"\bPARTITION\s+BY\b", "partitioning → see partitioning checks (DEFAULT partition, key in PK)"),
        (r"SYS_REFCURSOR|\bREF\s+CURSOR\b", "ref cursor → refcursor or set-returning function"),
        (r"%ROWTYPE|%TYPE\b", "anchored types → explicit target types or table rowtype"),
        (r"\bBULK\s+COLLECT\b|\bFORALL\b", "bulk binds → set-based SQL / arrays"),
        (r"\bEXECUTE\s+IMMEDIATE\b", "dynamic SQL → EXECUTE format(...) with %I/%L quoting"),
        (r"\bPRAGMA\s+AUTONOMOUS_TRANSACTION\b", "autonomous transaction has no direct equivalent (dblink/redesign) — flag"),
        (r"\b(?:DBMS|UTL)_\w+", "Oracle-supplied package call → playbook special-features / orafce"),
        (r"\bRAISE_APPLICATION_ERROR\b", "RAISE_APPLICATION_ERROR → RAISE EXCEPTION ... USING ERRCODE (keep the code mapping consistent)"),
        (r"\bTABLE\s+OF\b|\bVARRAY\b", "collections → arrays / SETOF composite (one RETURN NEXT per element)"),
        (r"\bCOMMIT\b|\bROLLBACK\b", "transaction control inside code → procedure (not function); caller owns the txn"),
        (r"\bGLOBAL\s+TEMPORARY\b", "global temporary table → temp table created per session / unlogged"),
        (r"\bDECODE\s*\(|\bNVL2?\s*\(", "DECODE/NVL → CASE/COALESCE (NULL-safe comparison)"),
        (r"\.NEXTVAL\b|\.CURRVAL\b", "sequence access → nextval()/currval()/identity"),
        (r"\bMERGE\s+INTO\b", "MERGE → INSERT ... ON CONFLICT (or PG15+ MERGE)"),
    ],
    "sqlserver": [
        (r"\bIDENTITY\b", "IDENTITY → GENERATED ... AS IDENTITY; reset after load"),
        (r"\bTOP\s*\(?\d", "TOP → LIMIT (mind ORDER BY / WITH TIES)"),
        (r"\b(?:CROSS|OUTER)\s+APPLY\b", "APPLY → LATERAL join"),
        (r"\bMERGE\b", "MERGE → INSERT ... ON CONFLICT (or PG15+ MERGE)"),
        (r"@@ROWCOUNT|@@IDENTITY|SCOPE_IDENTITY", "@@ROWCOUNT/SCOPE_IDENTITY → GET DIAGNOSTICS / RETURNING"),
        (r"\bBEGIN\s+TRY\b|\bTHROW\b|\bRAISERROR\b", "TRY/CATCH/THROW → EXCEPTION blocks / RAISE"),
        (r"#\w+", "#temp tables → CREATE TEMP TABLE"),
        (r"\bhierarchyid\b|\bgeography\b|\bgeometry\b", "hierarchyid/spatial types → ltree/PostGIS or text (see datatype map)"),
        (r"\bNOLOCK\b", "NOLOCK hint → remove (MVCC)"),
        (r"\bOUTPUT\s+(?:INSERTED|DELETED)\b", "OUTPUT clause → RETURNING"),
        (r"\bsp_executesql\b|\bEXEC\s*\(", "dynamic SQL → EXECUTE format(...)"),
        (r"\bCURSOR\b", "cursor → FOR loop over query / set-based rewrite"),
        (r"\bCOMMIT\b|\bROLLBACK\b|\bBEGIN\s+TRAN", "transaction control inside code → procedure; caller owns the txn"),
        (r"\bDATEADD\s*\(|\bDATEDIFF\s*\(|\bDATEPART\s*\(|\bGETDATE\s*\(|\bSYSDATETIME\s*\(",
         "date functions → interval arithmetic / date_part; DATEDIFF counts boundaries (current_date - d::date for DAY)"),
        (r"\bCONVERT\s*\(|\bFORMAT(?:MESSAGE)?\s*\(", "CONVERT/FORMAT(MESSAGE) → CAST / to_char / format() (style codes and NULL rendering differ)"),
        (r"\bISNULL\s*\(|\bIIF\s*\(|\bCHOOSE\s*\(", "ISNULL/IIF/CHOOSE → COALESCE / CASE / array index"),
        (r"\bREPLICATE\s*\(|\bDATALENGTH\s*\(|\bLEN\s*\(|\bCHARINDEX\s*\(|\bSTUFF\s*\(",
         "string functions → repeat/lpad, octet_length, length (LEN ignores trailing spaces), strpos, overlay"),
        (r"\bTOP\s*\(?\s*\d+\s*\)?\s*PERCENT\b", "TOP n PERCENT → row_number() <= ceil(count * n / 100)"),
        (r"\bERROR_(?:NUMBER|MESSAGE|SEVERITY|STATE|LINE|PROCEDURE)\s*\(|\bRAISERROR\b",
         "ERROR_*() / RAISERROR → GET STACKED DIAGNOSTICS in the handler; pass fields to logging procs"),
        (r"\bCURRENT_USER\b|\bSUSER_S?NAME\s*\(|\bUSER_NAME\s*\(", "CURRENT_USER/SUSER_SNAME → current_user/session_user (DB user vs login differ — BEHAVIOURAL)"),
        (r"'\s*\+|\+\s*'", "'+' string concatenation → '||' (NULL handling: CONCAT_NULL_YIELDS_NULL)"),
        (r"\bWITH\s+SCHEMABINDING\b|\bSET\s+NOCOUNT\b|\bWITH\s+EXECUTE\s+AS\b", "SCHEMABINDING / SET NOCOUNT / EXECUTE AS → drop (no equivalent needed)"),
        (r"\bOPTION\s*\(\s*MAXRECURSION", "MAXRECURSION → recursion-level guard in WITH RECURSIVE"),
        (r"\bCURSOR\s+VARYING\s+OUTPUT\b", "cursor OUTPUT param → set-returning function (or refcursor)"),
    ],
}


def detect_constructs(source_text: str, pair: str) -> List[str]:
    """Hints for constructs present in this object's source (comments stripped)."""
    body = re.sub(r"--[^\n]*", " ", source_text or "")
    body = re.sub(r"/\*.*?\*/", " ", body, flags=re.DOTALL)
    return [hint for pat, hint in _CONSTRUCT_HINTS.get(_source_engine(pair), [])
            if re.search(pat, body, re.IGNORECASE)]


def _hints_block(source_text: str, pair: str) -> str:
    hints = detect_constructs(source_text, pair)
    if not hints:
        return ""
    return ("=== CONSTRUCTS DETECTED IN THIS PROMPT'S SOURCE (apply the matching guidance in "
            "the context) ===\n" + "\n".join(f"- {h}" for h in hints) + "\n\n")


def build_unit_prompt(units, repo_root: Optional[Path] = None,
                      pair: Optional[str] = None,
                      shared_context: Optional[str] = None) -> str:
    """Build a conversion prompt for one or more object-units (a batch).

    ``units`` is an ObjectUnit or a list of them. With ``shared_context`` (the
    file written by :func:`write_shared_context`) the context is referenced, not
    inlined.
    """
    if not isinstance(units, (list, tuple)):
        units = [units]
    root = repo_root or config.find_repo_root()
    pair = pair or config.active_pair()
    context = _context_or_ref(shared_context, root, pair, SCHEMA)
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
        f"=== TASK ===\n"
        f"{_instruction(src_disp, _target_engine(pair), code=False, target_schema=(units[0].schema or '').lower() or None)}\n\n"
        f"{_hints_block(source_block, pair)}"
        f"{source_block}\n"
    )


def build_code_prompt(code_objs, repo_root: Optional[Path] = None,
                      pair: Optional[str] = None,
                      shared_context: Optional[str] = None) -> str:
    """Conversion prompt for one code object or a batch of small ones."""
    if not isinstance(code_objs, (list, tuple)):
        code_objs = [code_objs]
    root = repo_root or config.find_repo_root()
    pair = pair or config.active_pair()
    context = _context_or_ref(shared_context, root, pair, CODE)
    sources = "\n\n".join(
        f"--- SOURCE ({o.object_type}) — {o.schema}.{o.name} ---\n{o.source_ddl}"
        for o in code_objs)
    plural = (" Each object below is independent: convert each one and save it to "
              "its own output file (listed in the header)." if len(code_objs) > 1 else "")
    return (
        f"{context}\n\n"
        f"=== TASK ===\n"
        f"{_instruction(_source_display(pair), _target_engine(pair), code=True, target_schema=(code_objs[0].schema or '').lower() or None)}{plural}\n\n"
        f"{_hints_block(sources, pair)}"
        f"{sources}\n"
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
- **Schema-qualify every table in source_sql** (`<SCHEMA>.<table>`) — the source
  login is often not the schema owner. (run-tests also sets the source session
  schema where the engine supports it, but qualification is the portable guard.)
- **Set-returning functions** (Oracle PIPELINED / table functions, SQL Server TVFs,
  converted to `RETURNS TABLE` / `SETOF`): ALWAYS include at least one *execution*
  case that actually selects from the function — e.g.
  `SELECT COUNT(*) FROM TABLE(<schema>.<fn>(<args>))` vs
  `SELECT COUNT(*) FROM <schema>.<fn>(<args>)`, plus a checksum/aggregate over a
  returned column. A declared RETURNS TABLE column type that differs from the query's
  actual type (e.g. `numeric` vs `bigint`) compiles fine and fails only at execution.
- If the tables an object reads are EMPTY in the sampled data, say so in `notes:` —
  the case only exercises the empty/default path (reported as LOW_COVERAGE).
- For packages, generate cases for the public subprograms a caller would use. A package
  spec may mix both shapes: set `type: function` or `type: procedure` on each CASE to
  override the spec-level `type`.
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
        return ("(no sample rows: this object reads no schema table, or every table it "
                "reads is empty in the source — see notes/LOW_COVERAGE)")

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
                      pair: Optional[str] = None,
                      shared_context: Optional[str] = None,
                      target_code: Optional[str] = None) -> str:
    """Single-object test prompt (see :func:`build_test_batch_prompt`)."""
    return build_test_batch_prompt(
        [{"obj_type": obj_type, "name": name, "source_ddl": source_ddl,
          "target_code": target_code}],
        schema, sample, repo_root=repo_root, pair=pair, shared_context=shared_context)


def _shape(obj_type: str) -> str:
    t = (obj_type or "").upper()
    return ("function" if t.startswith("FUNC") else
            "procedure" if t.startswith("PROC") else "function and/or procedure")


def build_test_batch_prompt(objs, schema: str, sample: dict,
                            repo_root: Optional[Path] = None,
                            pair: Optional[str] = None,
                            shared_context: Optional[str] = None) -> str:
    """Prompt for the assistant to write equivalence-test specs for one or more
    objects (``objs`` = dicts with obj_type, name, source_ddl, target_code).

    Per object: its source and the CONVERTED target code when available (so target
    calls use the real flattened names/signatures instead of guesses). Sampled real
    data is included once for the union of tables the batch reads. The phase
    context (spec format + test-relevant engine checks + customer rules) is
    referenced via ``shared_context`` or inlined when absent.
    """
    root = repo_root or config.find_repo_root()
    pair = pair or config.active_pair()
    target = _target_engine(pair)
    context = _context_or_ref(shared_context, root, pair, TESTS)
    tname = _DISPLAY.get(target, target)
    sections = []
    for o in objs:
        tc = o.get("target_code")
        tgt = (f"--- CONVERTED TARGET CODE ({tname}) — use these exact routine names "
               f"and signatures in target_sql / call_target ---\n{tc}\n"
               if tc else
               "--- CONVERTED TARGET CODE --- (not available yet — derive target names "
               "from the conversion log / code manifest; packages are flattened to "
               "<package>_<subprogram>)\n")
        sections.append(
            f"### {o['obj_type']} {schema}.{o['name']} — write a **{_shape(o['obj_type'])}**"
            f"-shape spec\n"
            f"--- SOURCE ({o['obj_type']}) — {schema}.{o['name']} ---\n{o['source_ddl']}\n\n"
            f"{tgt}")
    what = (f"the converted {_target_display(target)} {objs[0]['obj_type'].lower()} "
            f"`{schema}.{objs[0]['name']}`" if len(objs) == 1 else
            f"each of the {len(objs)} converted {_target_display(target)} objects below "
            "(one spec file per object, as listed in the header)")
    return (
        f"{context}\n\n"
        f"=== TASK — GENERATE EQUIVALENCE TESTS ===\n"
        f"Generate equivalence tests that prove {what} behaves the same as the "
        f"{_source_display(pair)} source: same input → same return value (functions) or "
        f"same net effect (procedures). Tests run on BOTH engines and the results are "
        f"compared. Use the spec format and Rules in the context above.\n\n"
        + "\n".join(sections) +
        f"\n--- SAMPLED REAL DATA (use these actual values) ---\n{_format_sample(sample)}\n"
    )
