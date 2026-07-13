"""Parse an LLM response into executable DDL.

The converting LLM (Kiro) writes its answer into the unit's output ``.sql`` file.
That answer may contain Markdown code fences or surrounding prose; this module
extracts the runnable SQL so ``apply-schema`` can execute it directly.
"""
from __future__ import annotations

import re
from typing import List

# Capture the fence's language tag (group 1) and body (group 2) so non-SQL blocks
# (e.g. ```text / ```json explanatory output) can be filtered out.
_FENCE_RE = re.compile(
    r"```([A-Za-z0-9_+-]*)\s*\n(.*?)```",
    re.DOTALL,
)

# Language tags we treat as executable SQL. An empty tag (``` ) is allowed but the
# body is still validated with ``looks_like_sql`` before it is accepted.
_SQL_TAGS = {
    "", "sql", "plpgsql", "pgsql", "postgresql", "postgres", "plsql", "psql",
    "tsql", "mysql", "mariadb", "oraclesql", "ddl",
}


def parse_ddl(text: str) -> str:
    """Return executable SQL extracted from an LLM response.

    - If fenced code blocks are present, concatenate only those whose language tag
      names a SQL dialect (or is empty and whose body *looks like* SQL). Blocks
      tagged ``text``/``json``/etc. are explanatory prose and are dropped so they
      are never shipped to the target as DDL.
    - If fences are present but none qualify as SQL, fall back to concatenating all
      fenced bodies (best-effort — avoids silently returning nothing).
    - If no fences are present, return the stripped text as-is.
    """
    if not text:
        return ""
    matches = [(m.group(1).strip().lower(), m.group(2).strip())
               for m in _FENCE_RE.finditer(text)]
    if matches:
        selected: List[str] = []
        for tag, body in matches:
            if not body:
                continue
            if tag in _SQL_TAGS and (tag != "" or looks_like_sql(body)):
                selected.append(body)
        if selected:
            return "\n\n".join(selected).strip() + "\n"
        # No block qualified as SQL — fall back to all non-empty bodies rather than
        # returning nothing (the caller/apply step will surface a real error).
        bodies = [body for _, body in matches if body]
        if bodies:
            return "\n\n".join(bodies).strip() + "\n"
    return text.strip() + "\n"


def looks_like_sql(text: str) -> bool:
    """Heuristic sanity check that parsed text contains DDL/DML."""
    if not text or not text.strip():
        return False
    keywords = ("CREATE", "ALTER", "COMMENT", "GRANT", "INSERT", "DROP",
                "BEGIN", "DO", "SET")
    head = text.lstrip().upper()
    return any(head.startswith(k) or f"\n{k} " in f"\n{head}" for k in keywords)
