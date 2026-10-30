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
        proc = ("MySQL stored-program SQL: BEGIN … END, DECLARE … HANDLER, SIGNAL"
                if target == "mysql" else "PL/pgSQL")
        return (f"Convert the following {source_disp} stored code object to {tdisp} "
                f"({proc}). Return only valid {tdisp}, ready to "
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
             "ansi-sql", "deprecated-features"},
    CODE: {"sql-plsql", "tsql", "ansi-sql", "special-features", "deprecated-features"},
    TESTS: set(),
}
# Playbook files injected in FULL for a phase (relative to the playbook references
# dir). quick-tips is the pair's checklist of common gotchas; it is short and is the
# file the playbook tells the converter to read first.
_PHASE_FULL_FILES = {
    SCHEMA: ("quick-tips/quick-tips.md",),
    CODE: ("quick-tips/quick-tips.md",),
    TESTS: (),
}
# engines/<pair>/checks/* files routed per phase (by stem).
_TEST_CHECKS = {"equivalence-spec", "package-naming"}


def _markdown_sections(text: str, prefixes) -> str:
    """Return the ``## `` sections of ``text`` whose heading starts with one of
    ``prefixes`` (case-insensitive), in document order."""
    wanted = [p.lower() for p in prefixes or ()]
    parts = re.split(r"(?m)^(?=## )", text or "")
    keep = [part.strip() for part in parts
            if part.startswith("## ")
            and any(part[3:].lower().startswith(w) for w in wanted)]
    return "\n\n".join(keep)


def _version_key(target: str, version: str) -> str:
    """Comparable major version: PostgreSQL ``17.7`` → ``17``; MySQL ``8.4.x`` → ``8.4``
    (Aurora MySQL 3.x is MySQL 8.0, so ``3.13`` → ``8.0``)."""
    v = str(version or "").strip().lower()
    nums = re.findall(r"\d+", v)
    if not nums:
        return ""
    if target == "mysql":
        if nums[0] == "3":
            return "8.0"
        return ".".join(nums[:2]) if len(nums) > 1 else nums[0]
    return nums[0]


def _baseline_version_note(target: str, version: str, verified) -> str:
    """Caution prepended to the baseline when the declared target version is not one
    the baseline was verified for (e.g. a PostgreSQL 18 baseline on a 17.7 target)."""
    verified = [str(x) for x in (verified or [])]
    if not verified:
        return ""
    key = _version_key(target, version)
    shown = ", ".join(verified)
    if not key:
        return (f"> **Target version not declared** (`target.version` in connections.yaml). "
                f"This baseline was verified on {shown}; confirm the target version before "
                "using version-specific defaults.\n\n")
    if key in verified:
        return ""
    return (f"> **CAUTION — target version {version} is not one this baseline was verified "
            f"on ({shown}).** Features the text marks as introduced in a later version "
            f"(for example \"PG 18\" or \"8.4 only\") are NOT available on {version}: use "
            "the older form given in the same row or section, and check anything "
            "version-specific against the target before relying on it.\n\n")


def _load_target_baseline(repo_root: Path, pair: str, phase: str,
                          target_version: Optional[str] = None) -> str:
    """Selected sections of the target-version baseline for this phase.

    Configured in engine.yaml under ``conversion.target_baseline``::

        target_baseline:
          file: skills/<playbook>/references/target-baseline-<target>.md
          verified_for: ["18"]          # major versions the file was validated on
          sections:
            schema: [Conversion defaults, Behavior differences]
            code:   [Conversion defaults, Behavior differences]
            tests:  [Behavior differences]

    When the declared target version (``target.version`` in connections.yaml, or
    ``target_version``) is not in ``verified_for``, a caution is prepended so 18-only
    or 8.4-only defaults are not applied to an older target.

    The baseline holds the verified defaults and traps for the target version
    (sql_mode, collation, removed features, version-specific breaks), which every
    conversion and every equivalence test depends on. Returns '' when unconfigured.
    """
    cfg = ((_engine_yaml(repo_root, pair).get("conversion") or {})
           .get("target_baseline") or {})
    rel = str(cfg.get("file") or "").strip()
    prefixes = (cfg.get("sections") or {}).get(phase) or []
    if not rel or not prefixes:
        return ""
    body = _markdown_sections(_read(repo_root, rel), prefixes)
    if not body:
        return ""
    version = config.target_version() if target_version is None else target_version
    note = _baseline_version_note(_target_engine(pair), version, cfg.get("verified_for"))
    return f"{note}Source: `{rel}`\n\n{body}"


def _chapter_index(chapter_dir: Path) -> str:
    """The chapter's ``_index.md``; for a chapter without one, a generated list of its
    topic files (title + conversion category) so the chapter is not silently dropped."""
    idx = chapter_dir / "_index.md"
    if idx.is_file():
        return idx.read_text()
    lines = []
    for f in sorted(chapter_dir.glob("*.md")):
        text = _read(chapter_dir.parent, f"{chapter_dir.name}/{f.name}")
        title = next((ln[2:].strip() for ln in text.splitlines() if ln.startswith("# ")),
                     f.stem)
        cat = re.search(r"\*\*Conversion category:\*\*\s*([^\n]+)", text)
        lines.append(f"- [{f.name}]({f.name}) — {title}"
                     + (f" ({cat.group(1).strip()})" if cat else ""))
    return (f"# {chapter_dir.name}/\n\n" + "\n".join(lines)) if lines else ""


def _phase_of(phase: Optional[str], for_code: bool) -> str:
    return phase or (CODE if for_code else SCHEMA)


def build_context(repo_root: Optional[Path] = None, *, for_code: bool = False,
                  pair: Optional[str] = None, phase: Optional[str] = None) -> str:
    """Build the context block for one phase (``schema`` | ``code`` | ``tests``).

    Engine-pair aware: selects the datatype map, checks, target-version baseline,
    quick tips, playbook indexes and customer-specific knowledge for the active pair. Customer-specific rules are
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
        baseline = _load_target_baseline(root, pair, phase)
        if baseline:
            blocks.append("# Target-version behavior differences to test for "
                          "(verified on the target version)\n\n" + baseline)
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

    # Target-version baseline: verified defaults and traps for the target version.
    baseline = _load_target_baseline(root, pair, phase)
    if baseline:
        blocks.append("# Target-version baseline — conversion defaults and traps "
                      "(verified on the target version; supersedes older playbook "
                      "text)\n\n" + baseline)

    idx_dir = root / paths["playbook"]
    # Short playbook files injected in full (the pair's quick-tips checklist).
    full = []
    for rel in _PHASE_FULL_FILES.get(phase, ()):
        body = _read(root, f"{paths['playbook']}/{rel}").strip()
        if body:
            full.append(f"Source: `{paths['playbook']}/{rel}`\n\n{body}")
    if full:
        blocks.append("# Playbook quick tips — common gotchas for this pair\n\n"
                      + "\n\n".join(full))

    # Topic indexes for the chapters relevant to this phase only.
    idx_text = []
    if idx_dir.is_dir():
        for chapter in sorted(d for d in idx_dir.iterdir() if d.is_dir()):
            if chapter.name not in _PHASE_CHAPTERS[phase]:
                continue
            body = _chapter_index(chapter)
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
#
# Each entry is (regex, {target: hint}, {target: topic file}). The hint depends on the
# TARGET engine as well as the source: a MySQL target must not be told to write
# PostgreSQL (ON CONFLICT, '||', EXECUTE format, nextval). The topic file is relative
# to ``skills/<pair>-playbook/references/`` and is rendered as a path so the assistant
# can open the refreshed detail (and cite it in the conversion log). A target with no
# hint text gets no hint for that construct. Every topic path is checked by a unit test.
PG, MY = "postgresql", "mysql"

_CONSTRUCT_HINTS = {
    "oracle": [
        (r"\bPIPELINED\b|\bPIPE\s+ROW\b",
         {PG: "PIPELINED table function → RETURNS TABLE/SETOF; declared column types must match the query's actual types (checked only at execution)",
          MY: "PIPELINED table function → MySQL has no table functions: a procedure returning a result set, a view, or JSON_TABLE; callers change"},
         {PG: "sql-plsql/user-defined-functions.md", MY: "sql-plsql/user-defined-functions.md"}),
        (r"\bCONNECT\s+BY\b",
         {PG: "hierarchical query → WITH RECURSIVE",
          MY: "hierarchical query → WITH RECURSIVE (depth limit: cte_max_recursion_depth)"},
         {PG: "sql-plsql/common-table-expressions.md", MY: "sql-plsql/common-table-expressions.md"}),
        (r"\bROWNUM\b",
         {PG: "ROWNUM applies BEFORE ORDER BY — reconstruct intent (LIMIT applies after)",
          MY: "ROWNUM applies BEFORE ORDER BY — reconstruct intent (LIMIT applies after; ROW_NUMBER() OVER for numbering)"},
         {}),
        (r"CTXSYS|\bCONTAINS\s*\(|\bSCORE\s*\(",
         {PG: "Oracle Text → tsvector/GIN redesign (decision item); do not create DR$ tables",
          MY: "Oracle Text → InnoDB FULLTEXT index + MATCH … AGAINST redesign (decision item); do not create DR$ tables"},
         {}),
        (r"\bPARTITION\s+BY\b",
         {PG: "partitioning → see partitioning checks (DEFAULT partition, key in PK)",
          MY: "partitioning → every unique key (incl. PK) must contain the partition columns; partitioned InnoDB tables cannot have foreign keys; LIST has no DEFAULT partition"},
         {PG: "physical-storage/table-partitioning-and-inheritance.md", MY: "physical-storage/table-partitioning.md"}),
        (r"SYS_REFCURSOR|\bREF\s+CURSOR\b",
         {PG: "ref cursor → refcursor or set-returning function",
          MY: "ref cursor → no cursor variables: return a result set from a procedure (final SELECT)"},
         {PG: "sql-plsql/cursors.md", MY: "sql-plsql/cursors.md"}),
        (r"%ROWTYPE|%TYPE\b",
         {PG: "anchored types → explicit target types or table rowtype",
          MY: "anchored types → explicit column types; records → one variable per field"},
         {PG: "sql-plsql/procedures-and-functions.md", MY: "sql-plsql/procedures-and-functions.md"}),
        (r"\bBULK\s+COLLECT\b|\bFORALL\b",
         {PG: "bulk binds → set-based SQL / arrays",
          MY: "bulk binds → set-based SQL or a temporary table (no collections)"},
         {PG: "sql-plsql/collections-and-bulk-operations.md", MY: "sql-plsql/cursors.md"}),
        (r"\bEXECUTE\s+IMMEDIATE\b",
         {PG: "dynamic SQL → EXECUTE format(...) with %I/%L quoting",
          MY: "dynamic SQL → PREPARE / EXECUTE … USING @vars / DEALLOCATE PREPARE (? placeholders, backtick identifiers); not allowed in stored functions or triggers"},
         {PG: "sql-plsql/execute-immediate-and-prepare.md", MY: "sql-plsql/execute-immediate-and-prepare.md"}),
        (r"\bPRAGMA\s+AUTONOMOUS_TRANSACTION\b",
         {PG: "autonomous transaction has no direct equivalent (dblink/redesign) — flag",
          MY: "autonomous transaction has no equivalent (no dblink) — redesign (separate connection from the app, or log after commit); flag"},
         {PG: "sql-plsql/transaction-model.md", MY: "sql-plsql/transaction-model.md"}),
        (r"\b(?:DBMS|UTL)_\w+",
         {PG: "Oracle-supplied package call → playbook special-features / orafce",
          MY: "Oracle-supplied package call → the DBMS_*/UTL_* files under sql-plsql/ (no orafce on MySQL)"},
         {}),
        (r"\bRAISE_APPLICATION_ERROR\b",
         {PG: "RAISE_APPLICATION_ERROR → RAISE EXCEPTION ... USING ERRCODE (keep the code mapping consistent)",
          MY: "RAISE_APPLICATION_ERROR → SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = …, MYSQL_ERRNO = … (SQLSTATE must be a literal; keep the code mapping consistent)"},
         {PG: "sql-plsql/procedures-and-functions.md", MY: "sql-plsql/procedures-and-functions.md"}),
        (r"\bTABLE\s+OF\b|\bVARRAY\b",
         {PG: "collections → arrays / SETOF composite (one RETURN NEXT per element)",
          MY: "collections → temporary table or JSON array (iterate with JSON_TABLE); MySQL has no collection types"},
         {PG: "sql-plsql/collections-and-bulk-operations.md"}),
        (r"\bCOMMIT\b|\bROLLBACK\b",
         {PG: "transaction control inside code → procedure (not function); caller owns the txn",
          MY: "transaction control inside code → procedure (functions and triggers cannot COMMIT/ROLLBACK); caller owns the txn"},
         {PG: "sql-plsql/transaction-model.md", MY: "sql-plsql/transaction-model.md"}),
        (r"\bGLOBAL\s+TEMPORARY\b",
         {PG: "global temporary table → temp table created per session / unlogged",
          MY: "global temporary table → CREATE TEMPORARY TABLE per session (no shared definition; cannot be referenced twice in one statement)"},
         {PG: "tables-indexes/temporary-tables.md"}),
        (r"\bDECODE\s*\(|\bNVL2?\s*\(",
         {PG: "DECODE/NVL → CASE/COALESCE (NULL-safe comparison)",
          MY: "DECODE/NVL → CASE / IFNULL / COALESCE (DECODE matches NULL = NULL: use <=>)"},
         {PG: "sql-plsql/single-row-and-aggregate-functions.md", MY: "sql-plsql/single-row-and-aggregate-functions.md"}),
        (r"\.NEXTVAL\b|\.CURRVAL\b",
         {PG: "sequence access → nextval()/currval()/identity",
          MY: "sequence access → MySQL has no sequences: AUTO_INCREMENT or a sequence table (LAST_INSERT_ID(expr) pattern)"},
         {PG: "sql-plsql/sequences.md", MY: "sql-plsql/sequences-and-auto-increment.md"}),
        (r"\bMERGE\s+INTO\b",
         {PG: "MERGE → native MERGE (PG15+) or INSERT ... ON CONFLICT",
          MY: "MERGE → INSERT … ON DUPLICATE KEY UPDATE (row-alias form; needs a unique key on the match columns) or UPDATE + INSERT; no MERGE in MySQL"},
         {PG: "sql-plsql/merge-statement.md", MY: "sql-plsql/merge-statement.md"}),
    ],
    "sqlserver": [
        (r"\bIDENTITY\b",
         {PG: "IDENTITY → GENERATED ... AS IDENTITY; reset after load",
          MY: "IDENTITY → AUTO_INCREMENT (must be the first column of some index); reseed after load (reset-identity)"},
         {PG: "tsql/identity-and-sequences.md", MY: "tsql/identity-sequences.md"}),
        (r"\bTOP\s*\(?\d",
         {PG: "TOP → LIMIT (mind ORDER BY / WITH TIES)",
          MY: "TOP → LIMIT (mind ORDER BY; WITH TIES and PERCENT have no LIMIT form)"},
         {PG: "tsql/top-fetch.md", MY: "tsql/top-fetch.md"}),
        (r"\b(?:CROSS|OUTER)\s+APPLY\b",
         {PG: "APPLY → LATERAL join",
          MY: "APPLY → JOIN LATERAL / LEFT JOIN LATERAL … ON TRUE"},
         {PG: "ansi-sql/table-join.md", MY: "ansi-sql/table-join.md"}),
        (r"\bMERGE\b",
         {PG: "MERGE → native MERGE (PG15+) or INSERT ... ON CONFLICT",
          MY: "MERGE → INSERT … ON DUPLICATE KEY UPDATE (row-alias form; needs a unique key on the match columns) or UPDATE + INSERT; no MERGE in MySQL"},
         {PG: "tsql/merge.md", MY: "tsql/merge.md"}),
        (r"@@ROWCOUNT|@@IDENTITY|SCOPE_IDENTITY",
         {PG: "@@ROWCOUNT/SCOPE_IDENTITY → GET DIAGNOSTICS / RETURNING",
          MY: "@@ROWCOUNT/SCOPE_IDENTITY → ROW_COUNT() / LAST_INSERT_ID(), read immediately after the statement"},
         {PG: "tsql/identity-and-sequences.md", MY: "tsql/identity-sequences.md"}),
        (r"\bBEGIN\s+TRY\b|\bTHROW\b|\bRAISERROR\b",
         {PG: "TRY/CATCH/THROW → EXCEPTION blocks / RAISE",
          MY: "TRY/CATCH → DECLARE … HANDLER (EXIT/CONTINUE; no UNDO); THROW/RAISERROR → SIGNAL / RESIGNAL"},
         {PG: "tsql/error-handling.md", MY: "tsql/error-handling.md"}),
        (r"#\w+",
         {PG: "#temp tables → CREATE TEMP TABLE",
          MY: "#temp tables → CREATE TEMPORARY TABLE (cannot be referenced twice in one statement — error 1137; no foreign keys)"},
         {MY: "ansi-sql/temporary-tables.md"}),
        (r"\bhierarchyid\b|\bgeography\b|\bgeometry\b",
         {PG: "hierarchyid/spatial types → ltree/PostGIS or text (see datatype map)",
          MY: "hierarchyid/spatial types → MySQL spatial types with SRID, hierarchyid → path string (see datatype map)"},
         {PG: "ansi-sql/data-types.md", MY: "ansi-sql/data-types.md"}),
        (r"\bNOLOCK\b",
         {PG: "NOLOCK hint → remove (MVCC)",
          MY: "NOLOCK hint → remove (InnoDB MVCC reads do not block)"},
         {PG: "performance-tuning/query-hints-and-plan-guides.md", MY: "performance-tuning/query-hints.md"}),
        (r"\bOUTPUT\s+(?:INSERTED|DELETED)\b",
         {PG: "OUTPUT clause → RETURNING",
          MY: "OUTPUT clause → MySQL has no RETURNING: re-select by key / LAST_INSERT_ID(), or capture in a trigger"},
         {PG: "tsql/delete-update-from.md", MY: "tsql/delete-update.md"}),
        (r"\bsp_executesql\b|\bEXEC\s*\(",
         {PG: "dynamic SQL → EXECUTE format(...)",
          MY: "dynamic SQL → PREPARE / EXECUTE … USING @vars / DEALLOCATE PREPARE; not allowed in stored functions or triggers"},
         {PG: "tsql/dynamic-sql.md", MY: "tsql/stored-procedures.md"}),
        (r"\bCURSOR\b",
         {PG: "cursor → FOR loop over query / set-based rewrite",
          MY: "cursor → DECLARE CURSOR + CONTINUE HANDLER FOR NOT FOUND (a SELECT … INTO with no rows also fires it); or a set-based rewrite"},
         {PG: "tsql/cursors.md", MY: "tsql/cursors.md"}),
        (r"\bCOMMIT\b|\bROLLBACK\b|\bBEGIN\s+TRAN",
         {PG: "transaction control inside code → procedure; caller owns the txn",
          MY: "transaction control inside code → procedure (functions and triggers cannot COMMIT/ROLLBACK); caller owns the txn"},
         {PG: "tsql/transactions.md", MY: "tsql/transactions.md"}),
        (r"\bDATEADD\s*\(|\bDATEDIFF\s*\(|\bDATEPART\s*\(|\bGETDATE\s*\(|\bSYSDATETIME\s*\(",
         {PG: "date functions → interval arithmetic / date_part; DATEDIFF counts boundaries (current_date - d::date for DAY)",
          MY: "date functions → DATE_ADD/INTERVAL, EXTRACT, NOW(3); SQL Server DATEDIFF counts boundaries — MySQL DATEDIFF is whole days, TIMESTAMPDIFF counts complete units"},
         {PG: "tsql/date-time-functions.md", MY: "tsql/datetime.md"}),
        (r"\bCONVERT\s*\(|\bFORMAT(?:MESSAGE)?\s*\(",
         {PG: "CONVERT/FORMAT(MESSAGE) → CAST / to_char / format() (style codes and NULL rendering differ)",
          MY: "CONVERT/FORMAT → CAST / DATE_FORMAT (style codes differ; MySQL FORMAT() is number formatting only)"},
         {PG: "tsql/cast-and-convert.md", MY: "tsql/datetime.md"}),
        (r"\bISNULL\s*\(|\bIIF\s*\(|\bCHOOSE\s*\(",
         {PG: "ISNULL/IIF/CHOOSE → COALESCE / CASE / array index",
          MY: "ISNULL/IIF/CHOOSE → IFNULL or COALESCE / IF() or CASE / ELT() (MySQL ISNULL(x) is a 1-argument NULL test)"},
         {}),
        (r"\bREPLICATE\s*\(|\bDATALENGTH\s*\(|\bLEN\s*\(|\bCHARINDEX\s*\(|\bSTUFF\s*\(",
         {PG: "string functions → repeat/lpad, octet_length, length (LEN ignores trailing spaces), strpos, overlay",
          MY: "string functions → REPEAT, LENGTH (bytes), CHAR_LENGTH (LEN ignores trailing spaces), LOCATE, INSERT()"},
         {PG: "tsql/string-functions.md", MY: "tsql/string-functions.md"}),
        (r"\bTOP\s*\(?\s*\d+\s*\)?\s*PERCENT\b",
         {PG: "TOP n PERCENT → row_number() <= ceil(count * n / 100)",
          MY: "TOP n PERCENT → ROW_NUMBER() OVER (…) <= CEIL(COUNT(*) OVER () * n / 100) in a derived table"},
         {PG: "tsql/top-fetch.md", MY: "tsql/top-fetch.md"}),
        (r"\bERROR_(?:NUMBER|MESSAGE|SEVERITY|STATE|LINE|PROCEDURE)\s*\(|\bRAISERROR\b",
         {PG: "ERROR_*() / RAISERROR → GET STACKED DIAGNOSTICS in the handler; pass fields to logging procs",
          MY: "ERROR_*() → GET DIAGNOSTICS CONDITION 1 … MYSQL_ERRNO, MESSAGE_TEXT, RETURNED_SQLSTATE in the handler"},
         {PG: "tsql/error-handling.md", MY: "tsql/error-handling.md"}),
        (r"\bCURRENT_USER\b|\bSUSER_S?NAME\s*\(|\bUSER_NAME\s*\(",
         {PG: "CURRENT_USER/SUSER_SNAME → current_user/session_user (DB user vs login differ — BEHAVIOURAL)",
          MY: "CURRENT_USER/SUSER_SNAME → CURRENT_USER() (the definer inside SQL SECURITY DEFINER routines) vs USER() (the login) — BEHAVIOURAL"},
         {}),
        (r"'\s*\+|\+\s*'",
         {PG: "'+' string concatenation → '||' (NULL handling: CONCAT_NULL_YIELDS_NULL)",
          MY: "'+' string concatenation → CONCAT() ('+' is numeric addition: 'a' + 'b' = 0 silently); CONCAT returns NULL if any argument is NULL, CONCAT_WS skips NULLs"},
         {PG: "tsql/string-functions.md", MY: "tsql/string-functions.md"}),
        (r"\bWITH\s+SCHEMABINDING\b|\bSET\s+NOCOUNT\b|\bWITH\s+EXECUTE\s+AS\b",
         {PG: "SCHEMABINDING / SET NOCOUNT / EXECUTE AS → drop (no equivalent needed)",
          MY: "SCHEMABINDING / SET NOCOUNT → drop; EXECUTE AS → SQL SECURITY DEFINER / INVOKER"},
         {PG: "tsql/stored-procedures.md", MY: "tsql/stored-procedures.md"}),
        (r"\bOPTION\s*\(\s*MAXRECURSION",
         {PG: "MAXRECURSION → recursion-level guard in WITH RECURSIVE",
          MY: "MAXRECURSION → SET SESSION cte_max_recursion_depth (or a level guard in WITH RECURSIVE)"},
         {PG: "ansi-sql/common-table-expressions.md", MY: "ansi-sql/cte.md"}),
        (r"\bCURSOR\s+VARYING\s+OUTPUT\b",
         {PG: "cursor OUTPUT param → set-returning function (or refcursor)",
          MY: "cursor OUTPUT param → no cursor parameters: return a result set from a procedure"},
         {PG: "tsql/cursors.md", MY: "tsql/cursors.md"}),
    ],
}


def detect_constructs(source_text: str, pair: str) -> List[str]:
    """Target-aware hints for constructs present in this object's source (comments
    stripped). Each hint ends with the playbook topic file to open, when there is one."""
    body = re.sub(r"--[^\n]*", " ", source_text or "")
    body = re.sub(r"/\*.*?\*/", " ", body, flags=re.DOTALL)
    target = _target_engine(pair)
    out: List[str] = []
    for pat, hints, topics in _CONSTRUCT_HINTS.get(_source_engine(pair), []):
        hint = hints.get(target)
        if not hint or not re.search(pat, body, re.IGNORECASE):
            continue
        topic = topics.get(target)
        out.append(f"{hint} — see `skills/{pair}-playbook/references/{topic}`"
                   if topic else hint)
    return out


def _hints_block(source_text: str, pair: str) -> str:
    hints = detect_constructs(source_text, pair)
    if not hints:
        return ""
    return ("=== CONSTRUCTS DETECTED IN THIS PROMPT'S SOURCE (apply the matching guidance; "
            "open the named playbook file when the context is not enough, and cite it in "
            "the conversion log) ===\n" + "\n".join(f"- {h}" for h in hints) + "\n\n")


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
        compare: scalar          # scalar | resultset (all rows/columns; add
                                 # `ordered: true` only when row order is defined)

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
- A routine converted to a procedure that RETURNS A RESULT SET (e.g. a PIPELINED function on
  MySQL) is compared with a function-shape case: `compare: resultset`, source
  `SELECT * FROM TABLE(<fn>(...))`, target `CALL <proc>(...)`.
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
