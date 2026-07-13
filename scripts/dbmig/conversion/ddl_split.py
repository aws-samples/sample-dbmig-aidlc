"""Split converted DDL into *pre-data* and *post-data* statements.

Foreign keys and triggers are best applied **after** the data load, not before:

* a ``FOREIGN KEY`` enforced during load forces parent rows to exist before child
  rows, so the loader would have to insert in dependency order (or fail);
* a row trigger fires during ``COPY``/``INSERT`` and can **rewrite** the values
  being loaded, diverging the target from the source.

So the apply step classifies each statement and defers those two kinds to a
post-data pass. Everything else — ``CREATE TABLE`` (with inline PK/UK/CHECK),
``CREATE INDEX``, ``CREATE SEQUENCE``, trigger *functions* — is pre-data and
applied up front so the tables are ready to receive data.

The splitter is quote-aware: it respects single/double quotes, line/block
comments, and PostgreSQL/MySQL ``$tag$ ... $tag$`` dollar-quoted bodies (so a
trigger function's body is never split at an internal semicolon).
"""
from __future__ import annotations

import re
from typing import List, Tuple

_DOLLAR_TAG = re.compile(r"\$[A-Za-z0-9_]*\$")


def split_statements(sql: str) -> List[str]:
    """Split a SQL script into individual statements on top-level ``;``.

    Semicolons inside string literals, quoted identifiers, comments, or
    dollar-quoted bodies do not terminate a statement.
    """
    stmts: List[str] = []
    buf: List[str] = []
    i, n = 0, len(sql)
    in_squote = in_dquote = in_line = in_block = False
    dollar = None  # active dollar-quote tag, e.g. "$$" or "$body$"

    while i < n:
        ch = sql[i]
        two = sql[i:i + 2]

        if in_line:
            buf.append(ch)
            if ch == "\n":
                in_line = False
            i += 1
        elif in_block:
            buf.append(ch)
            if two == "*/":
                buf.append(sql[i + 1])
                i += 2
                in_block = False
            else:
                i += 1
        elif dollar:
            if sql.startswith(dollar, i):
                buf.append(dollar)
                i += len(dollar)
                dollar = None
            else:
                buf.append(ch)
                i += 1
        elif in_squote:
            buf.append(ch)
            if ch == "'":
                if sql[i + 1:i + 2] == "'":   # '' escape
                    buf.append("'")
                    i += 2
                    continue
                in_squote = False
            i += 1
        elif in_dquote:
            buf.append(ch)
            if ch == '"':
                in_dquote = False
            i += 1
        elif two == "--":
            in_line = True
            buf.append(two)
            i += 2
        elif two == "/*":
            in_block = True
            buf.append(two)
            i += 2
        elif ch == "'":
            in_squote = True
            buf.append(ch)
            i += 1
        elif ch == '"':
            in_dquote = True
            buf.append(ch)
            i += 1
        elif ch == "$" and (m := _DOLLAR_TAG.match(sql, i)):
            dollar = m.group(0)
            buf.append(dollar)
            i += len(dollar)
        elif ch == ";":
            buf.append(ch)
            stmt = "".join(buf).strip()
            if stmt:
                stmts.append(stmt)
            buf = []
            i += 1
        else:
            buf.append(ch)
            i += 1

    tail = "".join(buf).strip()
    if tail:
        stmts.append(tail)
    return stmts


def _strip_leading_comments(stmt: str) -> str:
    s = stmt
    while True:
        s = s.lstrip()
        if s.startswith("--"):
            nl = s.find("\n")
            s = s[nl + 1:] if nl >= 0 else ""
        elif s.startswith("/*"):
            end = s.find("*/")
            s = s[end + 2:] if end >= 0 else ""
        else:
            return s


def is_post_data(stmt: str) -> bool:
    """True if a statement should be applied *after* the data load: a foreign-key
    constraint or a trigger definition.

    FK detection is anchored (``ADD [CONSTRAINT x] FOREIGN KEY``) rather than a bare
    substring test, so an ``ALTER TABLE ... ADD COLUMN`` whose text merely contains
    the words ``FOREIGN KEY`` (e.g. in a column name/comment/default literal) is no
    longer misclassified — the regex only matches when ``FOREIGN KEY`` immediately
    follows ``ADD`` or ``ADD CONSTRAINT <name>``.
    """
    s = _strip_leading_comments(stmt).strip()
    if _CREATE_TRIGGER_RE.match(s):
        return True
    if _ALTER_TABLE_RE.match(s) and _ADD_FK_RE.search(s):
        return True
    return False


# ---- FK / trigger recognition patterns -----------------------------------

# Optional constraint name: quoted ("..."/`...`/[...]) or a bare identifier.
_CONSTRAINT_NAME = r'(?:"[^"]+"|`[^`]+`|\[[^\]]+\]|[A-Za-z0-9_$#]+)'

_CREATE_TRIGGER_RE = re.compile(
    r"^CREATE\s+(?:OR\s+REPLACE\s+)?(?:CONSTRAINT\s+)?TRIGGER\b", re.IGNORECASE)
_ALTER_TABLE_RE = re.compile(r"^ALTER\s+TABLE\b", re.IGNORECASE)
_ADD_FK_RE = re.compile(
    rf"\bADD\s+(?:CONSTRAINT\s+{_CONSTRAINT_NAME}\s+)?FOREIGN\s+KEY\b", re.IGNORECASE)
_CREATE_TABLE_RE = re.compile(
    r"^CREATE\s+(?:(?:GLOBAL|LOCAL)\s+)?(?:(?:TEMP(?:ORARY)?|UNLOGGED)\s+)*TABLE\b",
    re.IGNORECASE)
# A *table-level* FK item inside a CREATE TABLE column list.
_FK_ITEM_RE = re.compile(
    rf"^\s*(?:CONSTRAINT\s+{_CONSTRAINT_NAME}\s+)?FOREIGN\s+KEY\b", re.IGNORECASE)


def _find_column_list(stmt: str):
    """Split a ``CREATE TABLE`` on its top-level column-list parentheses.

    Returns ``(prefix, body, suffix)`` where ``body`` is the content between the
    outer parens (excluding them), or ``None`` if a balanced top-level ``(...)``
    is not found. Quote- and comment-aware.
    """
    i, n = 0, len(stmt)
    in_s = in_d = in_bt = in_line = in_block = False
    depth = 0
    start = -1
    while i < n:
        ch = stmt[i]
        two = stmt[i:i + 2]
        if in_line:
            if ch == "\n":
                in_line = False
        elif in_block:
            if two == "*/":
                in_block = False
                i += 2
                continue
        elif in_s:
            if ch == "'":
                if stmt[i + 1:i + 2] == "'":
                    i += 2
                    continue
                in_s = False
        elif in_d:
            if ch == '"':
                in_d = False
        elif in_bt:
            if ch == "`":
                in_bt = False
        elif two == "--":
            in_line = True
            i += 2
            continue
        elif two == "/*":
            in_block = True
            i += 2
            continue
        elif ch == "'":
            in_s = True
        elif ch == '"':
            in_d = True
        elif ch == "`":
            in_bt = True
        elif ch == "(":
            if depth == 0:
                start = i
            depth += 1
        elif ch == ")":
            depth -= 1
            if depth == 0 and start >= 0:
                return stmt[:start], stmt[start + 1:i], stmt[i + 1:]
        i += 1
    return None


def _split_top_level_commas(body: str) -> List[str]:
    """Split a CREATE TABLE body into its top-level, comma-separated items.
    Commas inside nested parens, quotes, or comments do not split. Quote- and
    comment-aware; preserves each item's original text."""
    parts: List[str] = []
    buf: List[str] = []
    depth = 0
    in_s = in_d = in_bt = in_line = in_block = False
    i, n = 0, len(body)
    while i < n:
        ch = body[i]
        two = body[i:i + 2]
        if in_line:
            buf.append(ch)
            if ch == "\n":
                in_line = False
            i += 1
        elif in_block:
            buf.append(ch)
            if two == "*/":
                buf.append(body[i + 1])
                i += 2
                in_block = False
            else:
                i += 1
        elif in_s:
            buf.append(ch)
            if ch == "'":
                if body[i + 1:i + 2] == "'":
                    buf.append("'")
                    i += 2
                    continue
                in_s = False
            i += 1
        elif in_d:
            buf.append(ch)
            if ch == '"':
                in_d = False
            i += 1
        elif in_bt:
            buf.append(ch)
            if ch == "`":
                in_bt = False
            i += 1
        elif two == "--":
            in_line = True
            buf.append(two)
            i += 2
        elif two == "/*":
            in_block = True
            buf.append(two)
            i += 2
        elif ch == "'":
            in_s = True
            buf.append(ch)
            i += 1
        elif ch == '"':
            in_d = True
            buf.append(ch)
            i += 1
        elif ch == "`":
            in_bt = True
            buf.append(ch)
            i += 1
        elif ch == "(":
            depth += 1
            buf.append(ch)
            i += 1
        elif ch == ")":
            depth -= 1
            buf.append(ch)
            i += 1
        elif ch == "," and depth == 0:
            parts.append("".join(buf))
            buf = []
            i += 1
        else:
            buf.append(ch)
            i += 1
    if "".join(buf).strip():
        parts.append("".join(buf))
    return parts


def _table_name(prefix: str):
    """Extract the table name from a ``CREATE TABLE ...`` prefix (text before the
    column list). Returns None if it can't be isolated."""
    m = re.match(
        r"\s*CREATE\s+(?:(?:GLOBAL|LOCAL)\s+)?(?:(?:TEMP(?:ORARY)?|UNLOGGED)\s+)*"
        r"TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?(.+?)\s*$",
        prefix, re.IGNORECASE | re.DOTALL)
    if not m:
        return None
    name = m.group(1).strip()
    return name or None


def _extract_inline_fks(stmt: str):
    """Pull *table-level* inline FK constraints out of a ``CREATE TABLE`` into
    deferred ``ALTER TABLE ... ADD ...`` statements.

    Returns ``(new_create, [alter_stmts])``. An inline ``CONSTRAINT ... FOREIGN KEY
    ... REFERENCES`` (or bare ``FOREIGN KEY ...``) clause otherwise stays pre-data
    and re-imposes the parent-before-child load ordering the deferral exists to
    avoid. If nothing can be safely extracted, the statement is returned unchanged
    with an empty alter list (fail-safe: never corrupt DDL)."""
    split = _find_column_list(stmt)
    if not split:
        return stmt, []
    prefix, body, suffix = split
    items = _split_top_level_commas(body)
    if not items:
        return stmt, []
    fk_items = [it for it in items if _FK_ITEM_RE.match(it)]
    if not fk_items:
        return stmt, []
    keep = [it for it in items if not _FK_ITEM_RE.match(it)]
    if not keep:
        return stmt, []  # a table of only FK clauses can't be right — bail safely
    name = _table_name(prefix)
    if not name:
        return stmt, []
    new_create = f"{prefix.rstrip()} (" + ",".join(keep) + f"\n){suffix.rstrip()}"
    alters = [f"ALTER TABLE {name} ADD {it.strip()}" for it in fk_items]
    return new_create, alters


def _join(stmts: List[str]) -> str:
    return "\n".join(s if s.rstrip().endswith(";") else s + ";"
                     for s in stmts).strip()


def partition_ddl(sql: str) -> Tuple[str, str]:
    """Return ``(pre_sql, post_sql)``: pre-data DDL and deferred (FK + trigger)
    DDL, each a runnable script (possibly empty). Inline table-level FK constraints
    inside ``CREATE TABLE`` are extracted into deferred ``ALTER TABLE ADD`` post-data
    statements so they never force parent-before-child load ordering."""
    pre: List[str] = []
    post: List[str] = []
    for st in split_statements(sql):
        if is_post_data(st):
            post.append(st)
            continue
        head = _strip_leading_comments(st).strip()
        if _CREATE_TABLE_RE.match(head):
            new_create, fk_alters = _extract_inline_fks(st)
            pre.append(new_create)
            post.extend(fk_alters)
        else:
            pre.append(st)
    return _join(pre), _join(post)
