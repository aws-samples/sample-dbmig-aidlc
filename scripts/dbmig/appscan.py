"""Application scanner library for the app-modernization module (``dbmig app-scan``).

Deterministic, single pass, read-only. Designed for large code bases (1,000s of
files): every file is read once, strings are tokenized in O(n), and the output is
an index the assistant uses to open ONLY the files that matter.

Coverage (the stacks named by the app-modernization skills and engine app rules):

* String literals per language — Java/Kotlin/Scala/Groovy (``"…" +`` joins, text
  blocks), C# (verbatim ``@"…"``, raw ``\"\"\"…\"\"\"``, interpolated ``$"…"``), Python
  (all quote kinds, triple quotes, implicit concatenation), JS/TS (``'…'``, ``"…"``,
  template literals), Go (raw back-quoted), SQL files, XML mappers (MyBatis/iBatis,
  Hibernate ``hbm.xml``/``orm.xml`` named queries).
* Entity / model mappings — JPA/Hibernate (Java/Kotlin annotations), EF Core
  (data annotations + fluent ``modelBuilder.Entity<T>`` / ``IEntityTypeConfiguration``,
  ``DbSet`` conventions, inherited base-class properties), SQLAlchemy (classic
  ``Column`` and 2.0 ``mapped_column``), Django models, TypeORM, Sequelize
  (``define`` / ``init``), Prisma schema.
* Framework detection — also Spring Data JDBC/JdbcTemplate, MyBatis, jOOQ,
  NHibernate, EF6, Dapper, ADO.NET, raw Python drivers, Knex, node drivers.
* Result-set typing sites (``rs.getInt``, ``reader.GetInt32``, ``reader["Col"]``),
  stored-routine calls, error-code handling, connection strings built in code.
"""
from __future__ import annotations

import bisect
import os
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, List, Optional, Tuple

EXCLUDE_DIRS = {"target", "build", "bin", "obj", "dist", "out", "node_modules", ".git",
                "vendor", "__pycache__", ".idea", ".vscode", ".gradle", ".mvn", ".venv",
                "venv", ".next", "coverage", "packages", ".vs", "TestResults", ".terraform"}
LANG = {".java": "java", ".kt": "java", ".kts": "java", ".scala": "java", ".groovy": "java",
        ".cs": "cs", ".vb": "vb", ".py": "py", ".js": "js", ".jsx": "js", ".ts": "js",
        ".tsx": "js", ".mjs": "js", ".cjs": "js", ".go": "go", ".rb": "rb", ".php": "php",
        ".sql": "sql", ".xml": "xml", ".prisma": "prisma"}
CONFIG_NAMES = re.compile(r"(^application.*\.(properties|ya?ml)$|^appsettings.*\.json$|"
                          r"^web\.config$|^app\.config$|^persistence\.xml$|^hibernate\.cfg\.xml$|"
                          r"^\.env|\.env$|^pom\.xml$|^build\.gradle(\.kts)?$|\.csproj$|"
                          r"^requirements.*\.txt$|^pyproject\.toml$|^package\.json$|"
                          r"^settings\.py$|^ormconfig\.|^knexfile\.|^database\.ya?ml$|"
                          r"^docker-compose.*\.ya?ml$|\.tf$|values.*\.ya?ml$)", re.I)
# Vendored front-end assets (jQuery, bootstrap, …) — never database code.
VENDORED = re.compile(r"(^|/)(wwwroot/lib|static/(?:vendor|lib|libs)|assets/(?:vendor|lib|libs)|"
                      r"public/(?:vendor|lib|libs)|third[_-]?party)(/|$)|\.min\.(js|css)$|"
                      r"(^|/)(jquery|bootstrap|popper|underscore|lodash|moment)[\w.-]*\.js$", re.I)
LEFTOVER = re.compile(r"\.(bak|orig|old|backup|save|swp)$|~$", re.I)
MAX_BYTES = 2_000_000

# ---- regex catalogue ---------------------------------------------------------

# A literal "looks like SQL" only with statement STRUCTURE, not a bare keyword
# ("call me later", "select a file" are English).
SQL_HINT_RE = re.compile(
    r"\bSELECT\b[\s\S]*?\bFROM\b|\bSELECT\s+(?:[\w.]+\s*\(|\d|\*|'|[\w.]+\s*(?:,|$|FROM))|"
    r"\bINSERT\s+INTO\b|\bUPDATE\s+[\w.\[\]\"`]+\s+SET\b|\bDELETE\s+FROM\b|\bMERGE\s+INTO\b|"
    r"\bWITH\s+\w+\s+AS\s*\(|\{\s*\??\s*=?\s*call\b|\bCALL\s+[\w.]+\s*\(|"
    r"(?-i:\bEXEC(?:UTE)?\s+[\w.\[])", re.I)
ROUTINE_RE = re.compile(r"\{\s*\??\s*=?\s*call\b|CallableStatement|prepareCall|"
                        r"@Procedure\b|@NamedStoredProcedureQuery|createStoredProcedureQuery|"
                        r"SimpleJdbcCall|CommandType\.StoredProcedure|"
                        r"[\"'`]\s*(?-i:EXEC(?:UTE)?)\s+[\w.\[]|"
                        r"callproc\(|ExecuteSqlRaw|ExecuteSqlInterpolated|"
                        r"statementType\s*=\s*\"CALLABLE\"",
                        re.I)
# Sites that BRANCH on a database error identity (not every `throws SQLException`).
ERROR_RE = re.compile(r"getErrorCode\s*\(|getSQLState\s*\(|ORA-\d{5}|\.Number\s*(?:==|!=|switch)|"
                      r"\.SqlState\b|\bcatch\s*\(\s*(?:\w+\.)*(?:Sql|Oracle|Postgres|Npgsql|MySql|"
                      r"DbUpdate|DataIntegrityViolation|SQLIntegrityConstraintViolation|DuplicateKey)"
                      r"\w*Exception|except\s+[\w.]*(?:IntegrityError|DatabaseError|OperationalError)|"
                      r"err\.(?:code|errorNum|number)\s*===?", re.I)
RESULTSET_RE = re.compile(r"\b(?:rs|resultSet|result)\.get(?:Int|Short|Long|Boolean|Date|"
                          r"Timestamp|Object|String|BigDecimal)\s*\(\s*\"|"
                          r"\.Get(?:Int16|Int32|Int64|Boolean|DateTime|Decimal|String|Byte)\s*\(|"
                          r"reader\s*\[\s*\"|\bdr\s*\[\s*\"|row\s*\[\s*['\"][A-Z_]+['\"]\s*\]",
                          re.I)
CONN_CODE_RE = re.compile(r"jdbc:[a-z0-9]+:|SqlConnectionStringBuilder|OracleConnectionStringBuilder|"
                          r"NpgsqlConnectionStringBuilder|MySqlConnectionStringBuilder|"
                          r"\bUse(?:SqlServer|Oracle|Npgsql|MySql|MySQL)\s*\(|Initial Catalog=|"
                          r"Data Source=|@//|oracledb\.connect|cx_Oracle\.connect|pyodbc\.connect|"
                          r"pymssql\.connect|create_engine\s*\(|new Sequelize\s*\(|DataSource\s*\(\s*\{|"
                          r"knex\s*\(\s*\{|mssql\+|oracle\+|postgresql\+|mysql\+")
CONFIG_KEYS_RE = re.compile(r"(jdbc:[a-z0-9:]+|oracle\.jdbc|OracleDriver|OracleDialect|"
                            r"SQLServerDriver|SQLServerDialect|sqlserver|ojdbc\d*|mssql-jdbc|"
                            r"Oracle\.ManagedDataAccess|Microsoft\.Data\.SqlClient|"
                            r"System\.Data\.SqlClient|Npgsql|Pomelo|MySql\.Data|"
                            r"EntityFrameworkCore\.\w+|ConnectionStrings?|"
                            r"ddl-auto|hibernate\.dialect|database-platform|"
                            r"ENGINE['\"]?\s*:|DATABASES|dialect|"
                            r"cx_Oracle|oracledb|pyodbc|pymssql|psycopg|mysqlclient|"
                            r"\"(?:oracledb|mssql|tedious|pg|mysql2?|sequelize|typeorm|knex|prisma)\"|"
                            r"postgresql|mysql)", re.I)
# Key must END in a secret word at a word boundary ("SaveToken" is a flag, "db.password" is not);
# boolean/null/placeholder values are not secrets.
SECRET_RE = re.compile(r"(?i)((?<![a-z])(?:[\w.-]*[._-])?(?:password|passwd|pwd|secret|api[_-]?key|"
                       r"access[_-]?key|client[_-]?secret|token)\s*[\"']?\s*[=:]\s*[\"']?)"
                       r"(?!(?:true|false|null|none|\[|\$\{|\{\{|%\(|<)[\s,;\"'<]*)([^\s,;\"'<]+)")

FRAMEWORKS = [  # (name, regex over code/config text)
    ("JPA/Hibernate", r"jakarta\.persistence|javax\.persistence|org\.hibernate|hibernate-core"),
    ("Spring Data JDBC/JdbcTemplate", r"JdbcTemplate|spring-boot-starter-jdbc|spring-data-jdbc"),
    ("MyBatis/iBatis", r"org\.apache\.ibatis|mybatis|<mapper\b|<sqlMap\b"),
    ("jOOQ", r"org\.jooq"),
    ("Raw JDBC", r"java\.sql\.(?:Connection|PreparedStatement|DriverManager)"),
    ("EF Core", r"Microsoft\.EntityFrameworkCore|\bDbContext\b"),
    ("EF6", r"System\.Data\.Entity\b"),
    ("NHibernate", r"NHibernate"),
    ("Dapper", r"using Dapper|\bDapper\b"),
    ("ADO.NET", r"\b(?:Sql|Oracle|Npgsql|MySql)(?:Connection|Command|DataReader)\b"),
    ("SQLAlchemy", r"\bsqlalchemy\b"),
    ("Django ORM", r"django\.db|from django"),
    ("Python DB-API driver", r"^\s*(?:import|from)\s+(?:cx_Oracle|oracledb|pyodbc|pymssql|psycopg2?|pymysql|MySQLdb)\b"),
    ("Sequelize", r"\bsequelize\b"),
    ("TypeORM", r"\btypeorm\b"),
    ("Knex", r"\bknex\b"),
    ("Prisma", r"@prisma/client|\bdatasource\s+db\s*\{"),
    ("Node DB driver", r"require\(['\"](?:oracledb|mssql|tedious|pg|mysql2?)['\"]\)|"  # nosemgrep: string-concat-in-list -- intentional: one long message split across lines
                       r"from ['\"](?:oracledb|mssql|tedious|pg|mysql2?)['\"]"),
]
# Full-text QUERY-language fragments built in app code (no SQL structure, so the
# SQL detector skips them) — e.g. a service composing "fuzzy(term, 40) OR ...".
# They silently never match after an Oracle Text / SQL Server FTS redesign.
TEXT_QUERY_RE = {
    "oracle": re.compile(r"\b(?:fuzzy|about|near|stem|soundex|nt|bt|syn)\s*\(|"
                         r"\bWITHIN\s+\w+|\$\w+|!\w+", re.I),
    "sqlserver": re.compile(r"\b(?:FORMSOF|NEAR|ISABOUT|INFLECTIONAL|THESAURUS)\s*\(", re.I),
}

FRAMEWORK_RES = [(n, re.compile(p, re.I | re.M)) for n, p in FRAMEWORKS]
# JS/TS files are only SQL-scanned when they use a Node DB driver/ORM (front-end
# code never talks to the database; scanning it only produces noise).
JS_DB_RE = re.compile(r"require\(['\"](?:oracledb|mssql|tedious|pg|mysql2?|sequelize|typeorm|knex|"
                      r"@prisma/client|mongodb)['\"]\)|from ['\"](?:oracledb|mssql|tedious|pg|mysql2?|"
                      r"sequelize|typeorm|knex|@prisma/client)['\"]|@Entity\s*\(")


# ---- walking -----------------------------------------------------------------

def walk(root: Path) -> Tuple[List[Path], List[Path], Counter]:
    files, leftovers, skipped = [], [], Counter()
    for dirpath, dirnames, filenames in os.walk(root):
        keep = []
        for d in dirnames:
            if d in EXCLUDE_DIRS:
                skipped[d] += 1
            else:
                keep.append(d)
        dirnames[:] = sorted(keep)
        for fn in sorted(filenames):
            p = Path(dirpath) / fn
            rel = str(p.relative_to(root)).replace(os.sep, "/")
            if LEFTOVER.search(fn):
                leftovers.append(p)
            elif VENDORED.search(rel):
                skipped["vendored-asset"] += 1
            elif p.suffix.lower() in LANG or CONFIG_NAMES.search(fn):
                files.append(p)
    return files, leftovers, skipped


# ---- string literal tokenizer --------------------------------------------------

_COMMENTS = {"java": ("//", "/*"), "cs": ("//", "/*"), "js": ("//", "/*"), "go": ("//", "/*"),
             "php": ("//", "/*"), "py": ("#", None), "rb": ("#", None), "vb": ("'", None),
             "sql": ("--", "/*")}


def string_literals(text: str, lang: str) -> List[Tuple[int, str]]:
    """``[(start_line, literal)]`` for every string literal in ``text``.

    Language-aware single pass: skips comments, handles triple-quoted / raw /
    verbatim / template strings, then merges literals joined only by ``+`` /
    whitespace (and, for Python, plain adjacency) so a statement split across
    lines is matched as ONE string starting at its first line."""
    line_comment, block_comment = _COMMENTS.get(lang, ("//", "/*"))
    n, i = len(text), 0
    lits: List[Tuple[int, int, str]] = []          # (start, end, content)
    while i < n:
        c = text[i]
        if line_comment and text.startswith(line_comment, i) and lang != "vb":
            j = text.find("\n", i)
            i = n if j < 0 else j
            continue
        if block_comment and text.startswith("/*", i):
            j = text.find("*/", i + 2)
            i = n if j < 0 else j + 2
            continue
        if lang in ("py", "java", "cs") and text.startswith(('"""', "'''") if lang == "py"
                                                           else ('"""',), i):
            q = text[i:i + 3]
            j = text.find(q, i + 3)
            j = n if j < 0 else j
            lits.append((i, j + 3, text[i + 3:j]))
            i = j + 3
            continue
        if lang == "cs" and c == '"' and i and text[i - 1] == "@" or \
                (lang == "cs" and c == '"' and text[max(0, i - 2):i] in ("$@", "@$")):
            j, buf = i + 1, []
            while j < n:
                if text[j] == '"':
                    if j + 1 < n and text[j + 1] == '"':
                        buf.append('"'); j += 2; continue
                    break
                buf.append(text[j]); j += 1
            lits.append((i, j + 1, "".join(buf)))
            i = j + 1
            continue
        if c in ('"', "'") or (c == "`" and lang in ("js", "go")):
            if c == "'" and lang in ("java", "cs", "vb"):   # char literal, not a string
                i += 1
                continue
            j, multiline = i + 1, c == "`"
            while j < n and text[j] != c:
                if text[j] == "\\" and lang != "go" or (text[j] == "\\" and c != "`"):
                    j += 2
                    continue
                if text[j] == "\n" and not multiline:
                    break
                j += 1
            lits.append((i, j + 1, text[i + 1:j]))
            i = j + 1
            continue
        i += 1
    # merge concatenations
    merged: List[Tuple[int, str]] = []
    joiner = re.compile(r"\s*\+?\s*" if lang in ("py",) else r"\s*\+\s*|\s*\.\s*(?=['\"])" if lang == "php"
                        else r"\s*\+\s*")
    k = 0
    while k < len(lits):
        s0, e0, body = lits[k]
        while k + 1 < len(lits):
            gap = text[e0:lits[k + 1][0]]
            if gap and joiner.fullmatch(gap) or (lang == "py" and not gap.strip()):
                body += lits[k + 1][2]
                e0 = lits[k + 1][1]
                k += 1
            else:
                break
        merged.append((s0, body))
        k += 1
    starts = [0]
    for m in re.finditer("\n", text):
        starts.append(m.end())
    return [(bisect.bisect_right(starts, s), b) for s, b in merged if b.strip()]


def _term_re(term: str) -> re.Pattern:
    t = re.escape(term.strip())
    lead = r"(?<![A-Za-z0-9_])" if term[:1].isalnum() else ""
    tail = r"(?![A-Za-z0-9_])" if term[-1:].isalnum() else ""
    return re.compile(lead + t + tail, re.I)


# ---- type categories ---------------------------------------------------------

_CAT = {
    "bool": {"boolean", "bool", "booleanfield", "nullbooleanfield"},
    "date": {"localdate", "java.sql.date", "dateonly", "date", "datefield", "dateonly"},
    "datetime": {"localdatetime", "instant", "offsetdatetime", "zoneddatetime", "timestamp",
                 "java.util.date", "datetime", "datetimeoffset", "datetimefield", "date_ts"},
    "int32": {"integer", "int", "short", "byte", "int32", "int16", "smallinteger",
              "integerfield", "smallintegerfield", "positiveintegerfield", "int?", "short?",
              "smallint", "tinyint", "mediumint"},
    "int64": {"long", "int64", "biginteger", "bigintegerfield", "bigint", "bigautofield"},
    "float": {"double", "float", "floatfield", "real", "single"},
    "decimal": {"bigdecimal", "decimal", "numeric", "decimalfield", "money"},
    "bytes": {"byte[]", "byte []", "largebinary", "binaryfield", "blob", "bytes", "buffer",
              "varbinary", "binary"},
    "string": {"string", "text", "charfield", "textfield", "varchar", "char", "clob",
               "emailfield", "slugfield", "urlfield", "nvarchar", "citext"},
    "guid": {"uuid", "guid", "uuidfield"},
}


def type_category(t: Optional[str]) -> str:
    if not t:
        return "other"
    x = t.strip().lower().replace("?", "").replace("system.", "")
    x = re.sub(r"^(?:mapped|optional)\[(.*)\]$", r"\1", x)
    x = re.sub(r"\(.*$", "", x).strip()
    x = x.split(".")[-1] if not x.startswith("java.") else x
    for cat, names in _CAT.items():
        if x in names:
            return cat
    return "other"


def target_category(data_type: Optional[str]) -> Optional[str]:
    if not data_type:
        return None
    t = data_type.lower()
    if t in ("smallint", "integer", "int", "mediumint", "tinyint"):
        return "int32" if t != "tinyint" else "tinyint"
    if t == "bigint":
        return "int64"
    if t in ("numeric", "decimal"):
        return "decimal"
    if t in ("real", "double precision", "double", "float"):
        return "float"
    if t in ("boolean", "bit"):
        return "bool"
    if t == "date":
        return "date"
    if t.startswith("timestamp") or t == "datetime":
        return "datetime"
    if t in ("bytea", "blob", "longblob", "mediumblob", "tinyblob", "varbinary", "binary"):
        return "bytes"
    if t == "uuid":
        return "guid"
    return "string"


# ---- mapping extractors --------------------------------------------------------
# Each returns entities: {class, table, schema, orm, file, quoted_default, fields:[...]}
# field: {field, java_type (declared type), column, lob, relation, jdbc_type_code,
#         column_definition, column_type (explicit DB type), explicit, line}


def _snake(name: str) -> str:
    return re.sub(r"(?<=[a-z0-9])([A-Z])", r"_\1", name).lower()


def _line(text: str, off: int) -> int:
    return text.count("\n", 0, off) + 1


_JPA_FIELD = re.compile(
    r"((?:@[\w.]+(?:\s*\((?:[^()]|\([^()]*\))*\))?\s*)*)"
    r"(?:(?:private|protected|public|internal)\s+)?(?:(?:final|lateinit|open)\s+)*"
    r"(?:(?:var|val)\s+(\w+)\s*:\s*([\w.<>\[\], ?]+?)|([\w.<>\[\], ]+?)\s+(\w+))\s*(?:=[^;\n]*)?[;\n,)]")


def extract_jpa(text: str, rel: str) -> List[dict]:
    if not re.search(r"@Entity\b|@Embeddable\b", text):
        return []
    out = []
    for cm in re.finditer(r"@Entity\b[\s\S]*?\bclass\s+(\w+)", text):
        name = cm.group(1)
        head = text[max(0, cm.start() - 400):cm.end()]
        tbl = re.search(r'@Table\s*\((?:[^)]*?\bname\s*=\s*)?"([^"]+)"', head)
        sch = re.search(r'@Table\s*\([^)]*?\bschema\s*=\s*"([^"]+)"', head)
        body_start = text.find("{", cm.end())
        end = _match_brace(text, body_start)
        body = text[body_start:end]
        fields = []
        for m in _JPA_FIELD.finditer(body):
            ann = m.group(1) or ""
            fname = m.group(2) or m.group(5)
            jtype = " ".join((m.group(3) or m.group(4) or "").split())
            mods = re.match(r"^((?:(?:private|protected|public|internal|final|static|transient|"
                            r"volatile|open|override)\s+)+)", jtype)
            if mods:
                if re.search(r"\b(static|transient)\b", mods.group(1)):
                    continue                    # not a persistent field
                jtype = jtype[mods.end():]
            if not fname or not jtype or jtype in ("return", "import", "package", "new", "class"):
                continue
            prefix = body[max(0, m.start() - 30):m.start()]
            if "static" in (m.group(0) + prefix).split() or "@Transient" in ann:
                continue
            if not ann.strip() and not re.match(r"\s*(private|protected|public|var|val)", m.group(0)):
                continue
            if re.search(r"@(OneToMany|ManyToMany|Embedded)\b", ann):
                continue
            cmn = re.search(r'@(?:Column|JoinColumn)\s*\((?:[^()]|\([^()]*\))*?\bname\s*=\s*"([^"]+)"', ann)
            rel_ = bool(re.search(r"@(ManyToOne|OneToOne)\b", ann))
            col = cmn.group(1) if cmn else (_snake(fname) + "_id" if rel_ else _snake(fname))
            jtc = re.search(r"@JdbcTypeCode\s*\(\s*SqlTypes\.(\w+)", ann)
            cdef = re.search(r'columnDefinition\s*=\s*"([^"]+)"', ann)
            fields.append({"field": fname, "java_type": jtype, "column": col.strip('"\\'),
                           "quoted": col.startswith(("\\\"", '"')) or '\\"' in (cmn.group(1) if cmn else ""),
                           "lob": "@Lob" in ann, "relation": rel_,
                           "jdbc_type_code": jtc.group(1) if jtc else None,
                           "column_definition": cdef.group(1) if cdef else None,
                           "line": _line(text, body_start + m.start())})
        out.append({"class": name, "table": (tbl.group(1) if tbl else _snake(name)),
                    "schema": sch.group(1) if sch else None, "orm": "JPA/Hibernate",
                    "file": rel, "fields": fields})
    return out


def _match_brace(text: str, start: int) -> int:
    if start < 0:
        return len(text)
    depth = 0
    for k in range(start, len(text)):
        ch = text[k]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return k + 1
    return len(text)


_CS_CLASS = re.compile(r"((?:\[[^\]]*\]\s*)*)(?:public|internal)\s+(?:(?:partial|abstract|sealed)\s+)*"
                       r"class\s+(\w+)(?:\s*<[^>]*>)?(?:\s*:\s*([\w.<>, ]+))?")
_CS_PROP = re.compile(r"((?:\[[^\]]*\]\s*)*)public\s+(?:(?:virtual|required|override|new)\s+)*"
                      r"([\w.<>?\[\], ]+?)\s+(\w+)\s*\{\s*(?:get|init)")
_CS_PRIM = {"string", "int", "long", "short", "byte", "bool", "decimal", "double", "float",
            "datetime", "datetimeoffset", "dateonly", "timeonly", "guid", "byte[]", "char",
            "timespan", "uint", "ulong", "ushort", "sbyte"}


def cs_classes(text: str, rel: str) -> Dict[str, dict]:
    """All C# classes in a file with their properties and attributes."""
    out = {}
    for m in _CS_CLASS.finditer(text):
        bstart = text.find("{", m.end())
        body = text[bstart:_match_brace(text, bstart)]
        attrs = m.group(1) or ""
        tbl = re.search(r'\[Table\(\s*"([^"]+)"(?:[^)]*Schema\s*=\s*"([^"]+)")?', attrs)
        props = []
        for p in _CS_PROP.finditer(body):
            pa, ptype, pname = p.group(1) or "", " ".join(p.group(2).split()), p.group(3)
            if "NotMapped" in pa:
                continue
            col = re.search(r'\[Column\(\s*"([^"]+)"', pa)
            ctype = re.search(r'TypeName\s*=\s*"([^"]+)"', pa)
            props.append({"field": pname, "java_type": ptype,
                          "column": col.group(1) if col else pname,
                          "explicit": bool(col), "column_type": ctype.group(1) if ctype else None,
                          "line": _line(text, bstart + p.start(3))})
        base = (m.group(3) or "").split(",")[0].strip().split("<")[0] or None
        out[m.group(2)] = {"class": m.group(2), "base": base, "file": rel, "props": props,
                           "table": tbl.group(1) if tbl else None,
                           "schema": tbl.group(2) if tbl else None}
    return out


def ef_model_config(text: str) -> Dict[str, dict]:
    """Fluent EF Core config per entity class: table, schema, per-property column/type."""
    cfg: Dict[str, dict] = {}
    blocks = []
    for m in re.finditer(r"\.Entity<(\w+)>\s*\(\s*(\w+)\s*=>\s*\{", text):
        blocks.append((m.group(1), text[m.end():_match_brace(text, m.end() - 1)]))
    for m in re.finditer(r"\.Entity<(\w+)>\s*\(\s*\)((?:\s*\.\w+\((?:[^()]|\([^()]*\))*\))+)", text):
        blocks.append((m.group(1), m.group(2)))
    for m in re.finditer(r"IEntityTypeConfiguration<(\w+)>", text):
        blocks.append((m.group(1), text[m.end():]))
    for cls, body in blocks:
        c = cfg.setdefault(cls, {"props": {}})
        t = re.search(r'\.ToTable\(\s*"([^"]+)"(?:\s*,\s*"([^"]+)")?', body)
        if t:
            c["table"], c["schema"] = t.group(1), t.group(2)
        for p in re.finditer(r'\.Property\(\s*\w+\s*=>\s*\w+\.(\w+)\s*\)((?:\s*\.\w+(?:<[^>]*>)?\((?:[^()]|\([^()]*\))*\))*)', body):
            chain = p.group(2)
            col = re.search(r'HasColumnName\(\s*"([^"]+)"', chain)
            ctype = re.search(r'HasColumnType\(\s*"([^"]+)"', chain)
            conv = re.search(r"HasConversion(?:<([\w?]+)>)?", chain)
            c["props"][p.group(1)] = {"column": col.group(1) if col else None,
                                      "column_type": ctype.group(1) if ctype else None,
                                      "conversion": (conv.group(1) or "custom") if conv else None}
    return cfg


def resolve_ef(classes: Dict[str, dict], dbsets: Dict[str, str],
               fluent: Dict[str, dict]) -> List[dict]:
    names = set(dbsets) | set(fluent) | {k for k, v in classes.items() if v["table"]}
    out = []
    for name in sorted(names):
        c = classes.get(name)
        if not c:
            continue
        props, seen, cur, depth = [], set(), c, 0
        while cur and depth < 6:               # inherited base-class properties
            for p in cur["props"]:
                if p["field"] not in seen:
                    seen.add(p["field"])
                    props.append(dict(p, file=cur["file"]))
            cur, depth = classes.get(cur["base"] or ""), depth + 1
        fl = fluent.get(name, {})
        fields = []
        for p in props:
            t = p["java_type"].replace("?", "").strip()
            low = t.lower()
            if low not in _CS_PRIM and (t in classes or re.match(r"(I?Collection|I?List|IEnumerable|HashSet)<", t)):
                continue                        # navigation property
            f = fl.get("props", {}).get(p["field"], {})
            col = f.get("column") or p["column"]
            fields.append({"field": p["field"], "java_type": p["java_type"], "column": col,
                           "quoted": not (f.get("column") or p["explicit"]),
                           "column_type": f.get("column_type") or p["column_type"],
                           "conversion": f.get("conversion"), "relation": False, "lob": False,
                           "line": p["line"], "decl_file": p["file"]})
        out.append({"class": name, "orm": "EF Core", "file": c["file"],
                    "table": fl.get("table") or c["table"] or dbsets.get(name) or name,
                    "schema": fl.get("schema") or c["schema"],
                    "table_quoted": not (fl.get("table") or c["table"]), "fields": fields})
    return out


_SA_COL = re.compile(r"^\s+(\w+)\s*(?::\s*Mapped\[([^\]]+)\])?\s*=\s*(?:\w+\.)?(Column|mapped_column)\s*\(([^\n]*)", re.M)
_DJ_FIELD = re.compile(r"^\s+(\w+)\s*=\s*models\.(\w+)\s*\(([^\n]*)", re.M)


def extract_python(text: str, rel: str) -> List[dict]:
    out = []
    for cm in re.finditer(r"^class\s+(\w+)\s*\(([^)]*)\)\s*:", text, re.M):
        nxt = re.search(r"^\S", text[cm.end():], re.M)
        body = text[cm.end(): cm.end() + (nxt.start() if nxt else len(text))]
        bases = cm.group(2)
        if "__tablename__" in body or re.search(r"\bBase\b|DeclarativeBase|db\.Model", bases):
            t = re.search(r"__tablename__\s*=\s*['\"]([^'\"]+)", body)
            sch = re.search(r"['\"]schema['\"]\s*:\s*['\"]([^'\"]+)", body)
            fields = []
            for f in _SA_COL.finditer(body):
                args = f.group(4)
                explicit = re.match(r"\s*['\"]([^'\"]+)['\"]", args)
                typ = re.search(r"\b(Boolean|Date|DateTime|LargeBinary|BigInteger|SmallInteger|Integer|"
                                r"Numeric|Float|Text|String|Unicode|LargeBinary|Uuid|UUID)\b", args)
                fields.append({"field": f.group(1), "java_type": (typ.group(1) if typ else f.group(2) or "?"),
                               "column": explicit.group(1) if explicit else f.group(1),
                               "relation": "ForeignKey" in args and False, "lob": False,
                               "line": _line(text, cm.end() + f.start(1))})
            if fields or t:
                out.append({"class": cm.group(1), "orm": "SQLAlchemy", "file": rel,
                            "table": t.group(1) if t else _snake(cm.group(1)),
                            "schema": sch.group(1) if sch else None, "fields": fields})
        elif re.search(r"models\.Model\b", bases):
            app = Path(rel).parent.name
            t = re.search(r"db_table\s*=\s*['\"]([^'\"]+)", body)
            fields = []
            for f in _DJ_FIELD.finditer(body):
                kind, args = f.group(2), f.group(3)
                if kind in ("ManyToManyField",):
                    continue
                dbc = re.search(r"db_column\s*=\s*['\"]([^'\"]+)", args)
                fk = kind in ("ForeignKey", "OneToOneField")
                fields.append({"field": f.group(1), "java_type": kind,
                               "column": dbc.group(1) if dbc else f.group(1) + ("_id" if fk else ""),
                               "relation": fk, "lob": False, "line": _line(text, cm.end() + f.start(1))})
            out.append({"class": cm.group(1), "orm": "Django ORM", "file": rel,
                        "table": t.group(1) if t else f"{app}_{cm.group(1).lower()}",
                        "schema": None, "fields": fields})
    return out


def extract_js(text: str, rel: str) -> List[dict]:
    out = []
    # TypeORM
    for cm in re.finditer(r"@Entity\s*\(\s*(?:['\"]([^'\"]+)['\"]|\{[^}]*?name\s*:\s*['\"]([^'\"]+)['\"][^}]*\})?\s*\)"
                          r"[\s\S]*?class\s+(\w+)", text):
        bstart = text.find("{", cm.end())
        body = text[bstart:_match_brace(text, bstart)]
        fields = []
        for f in re.finditer(r"@(Column|PrimaryGeneratedColumn|PrimaryColumn|CreateDateColumn|UpdateDateColumn)"
                             r"\s*\(([^)]*)\)\s*(\w+)\s*[!?]?\s*:\s*([\w\[\]<>| ]+)", body):
            args = f.group(2)
            nm = re.search(r"name\s*:\s*['\"]([^'\"]+)", args)
            ty = re.search(r"type\s*:\s*['\"]([^'\"]+)", args) or re.match(r"\s*['\"]([^'\"]+)", args)
            fields.append({"field": f.group(3), "java_type": f.group(4).strip(),
                           "column": nm.group(1) if nm else f.group(3),
                           "column_type": ty.group(1) if ty else None, "relation": False,
                           "lob": False, "line": _line(text, bstart + f.start(3))})
        out.append({"class": cm.group(3), "orm": "TypeORM", "file": rel,
                    "table": cm.group(1) or cm.group(2) or _snake(cm.group(3)),
                    "schema": None, "fields": fields})
    # Sequelize define / init
    for dm in re.finditer(r"(?:\.define\s*\(\s*['\"](\w+)['\"]\s*,|(\w+)\.init\s*\()\s*\{", text):
        bstart = dm.end() - 1
        bend = _match_brace(text, bstart)
        body = text[bstart:bend]
        opts = text[bend:bend + 400]
        tn = re.search(r"tableName\s*:\s*['\"]([^'\"]+)", opts)
        fields = []
        for f in re.finditer(r"\b(\w+)\s*:\s*(?:\{[^{}]*?type\s*:\s*)?(?:DataTypes|Sequelize)\.(\w+)", body):
            chunk = body[f.start(): body.find("}", f.end()) + 1 if "{" in body[f.start():f.end()] else f.end()]
            col = re.search(r"field\s*:\s*['\"]([^'\"]+)", chunk)
            fields.append({"field": f.group(1), "java_type": f.group(2),
                           "column": col.group(1) if col else f.group(1), "relation": False,
                           "lob": False, "line": _line(text, bstart + f.start(1))})
        name = dm.group(1) or dm.group(2)
        out.append({"class": name, "orm": "Sequelize", "file": rel,
                    "table": tn.group(1) if tn else name, "table_guess": not tn,
                    "schema": None, "fields": fields})
    return out


def extract_prisma(text: str, rel: str) -> List[dict]:
    out = []
    for mm in re.finditer(r"^model\s+(\w+)\s*\{", text, re.M):
        body = text[mm.end():_match_brace(text, mm.end() - 1)]
        tm = re.search(r'@@map\(\s*"([^"]+)"', body)
        sm = re.search(r'@@schema\(\s*"([^"]+)"', body)
        fields = []
        for f in re.finditer(r"^\s+(\w+)\s+(\w+)(\[\])?\??([^\n]*)", body, re.M):
            if f.group(1).startswith("@@") or f.group(3):
                continue
            attrs = f.group(4)
            if "@relation" in attrs:
                continue
            col = re.search(r'@map\(\s*"([^"]+)"', attrs)
            db = re.search(r"@db\.(\w+)", attrs)
            fields.append({"field": f.group(1), "java_type": f.group(2),
                           "column": col.group(1) if col else f.group(1),
                           "column_type": db.group(1) if db else None, "relation": False,
                           "lob": False, "line": _line(text, mm.end() + f.start(1))})
        out.append({"class": mm.group(1), "orm": "Prisma", "file": rel,
                    "table": tm.group(1) if tm else mm.group(1), "schema": sm.group(1) if sm else None,
                    "fields": fields})
    return out


# ---- obligations ---------------------------------------------------------------

_FIX = {  # (source situation) -> {orm: fix}
    "bool_on_int": {"JPA/Hibernate": "@JdbcTypeCode(SqlTypes.SMALLINT) (remove columnDefinition)",
                    "EF Core": ".HasConversion<short>() in OnModelCreating (or map the column to boolean)",
                    "SQLAlchemy": "use SmallInteger (or a Boolean TypeDecorator over smallint)",
                    "Django ORM": "use SmallIntegerField (or migrate the column to boolean)",
                    "*": "bind/read the flag as a small integer (0/1), not a boolean"},
    "date_on_ts": {"JPA/Hibernate": "keep LocalDate + @JdbcTypeCode(SqlTypes.TIMESTAMP)",
                   "EF Core": "use DateTime, or HasColumnType(\"timestamp\") + DateOnly converter",
                   "*": "map as a timestamp/datetime type (the migrated column carries time)"},
    "int_on_bigint": {"JPA/Hibernate": "Long, or @JdbcTypeCode(SqlTypes.BIGINT)",
                      "EF Core": "long", "*": "widen to a 64-bit integer type"},
    "lob_bytes": {"JPA/Hibernate": "drop @Lob, add @JdbcTypeCode(SqlTypes.VARBINARY)"},
    "lob_text": {"JPA/Hibernate": "drop @Lob (text maps to String)"},
    "float_on_decimal": {"*": "behavioural rounding — prefer an exact decimal type (BigDecimal/decimal/Decimal)"},
    "int_on_bool": {"EF Core": ".HasConversion(v => v != 0, v => v ? 1 : 0) in OnModelCreating (keeps the int model; "
                                "LINQ `x.Flag == 1` then translates to a boolean comparison)",
                    "JPA/Hibernate": "@Convert with an Integer<->Boolean AttributeConverter (or a boolean field)",
                    "*": "bind/compare the flag as a boolean, or change the column to smallint"},
    "dt_on_date": {"*": "BEHAVIOURAL: target column is date-only — the time part is dropped"},
    "ef_tz": {"EF Core": "Npgsql 6+: DateTime written to timestamptz must be DateTimeKind.Utc "
                          "(or enable Npgsql.EnableLegacyTimestampBehavior) — review"},
}


ADVISORY = "ADVISORY:"


def is_advisory(ob: Optional[str]) -> bool:
    return bool(ob) and ob.startswith(ADVISORY)


def _fix(kind: str, orm: str) -> str:
    d = _FIX[kind]
    return d.get(orm) or d.get("*") or next(iter(d.values()))


def obligation(field: dict, target_type: Optional[str], orm: str) -> Optional[str]:
    if not target_type or field.get("relation"):
        return None
    j, tt = type_category(field.get("java_type")), target_category(target_type)
    code, conv = field.get("jdbc_type_code"), field.get("conversion")
    if j == "bool" and tt in ("int32", "decimal") and code != "SMALLINT" and not conv:
        return f"Boolean on {target_type} column: " + _fix("bool_on_int", orm)
    if j == "int32" and tt == "bool" and not conv:
        return (f"integer field on {target_type} column (the source bit/NUMBER(1) accepted `= 1`; "
                "PostgreSQL raises 42883 boolean = integer): " + _fix("int_on_bool", orm))
    if j == "date" and tt == "datetime" and code != "TIMESTAMP" and not conv:
        return f"date-only type on {target_type} column: " + _fix("date_on_ts", orm)
    if j == "datetime" and tt == "date":
        return _fix("dt_on_date", orm)
    if field.get("lob") and tt == "bytes":
        return "@Lob on bytea (validates as oid): " + _fix("lob_bytes", orm)
    if field.get("lob") and tt == "string":
        return "@Lob String on text (validates as oid): " + _fix("lob_text", orm)
    if j == "int32" and tt == "int64" and code != "BIGINT" and not conv:
        if orm in ("JPA/Hibernate", "SQLAlchemy", "Django ORM"):
            # Hibernate validate accepts integral widening and JDBC/DB-API read int8
            # into a 32-bit value; the source column (e.g. NUMBER(10)) already
            # exceeded int32, so the overflow risk is pre-existing, not migration-made.
            return (f"{ADVISORY} 32-bit field on bigint column — not a boot blocker; "
                    "overflow risk pre-dates the migration. Widen only if values can exceed 2^31-1")
        return f"32-bit field on bigint column: " + _fix("int_on_bigint", orm)
    if j == "float" and tt == "decimal":
        return f"{ADVISORY} " + _fix("float_on_decimal", orm)
    if orm == "EF Core" and j == "datetime" and "with time zone" in (target_type or ""):
        return _fix("ef_tz", orm)
    cdef = field.get("column_definition") or field.get("column_type") or ""
    if re.search(r"\b(NUMBER|VARCHAR2|NVARCHAR2|NCLOB|CLOB|BLOB|RAW|NVARCHAR|NCHAR|NTEXT|"
                 r"DATETIME2|SMALLDATETIME|DATETIMEOFFSET|BIT|MONEY|SMALLMONEY|UNIQUEIDENTIFIER|"
                 r"IMAGE|ROWVERSION|HIERARCHYID|SQL_VARIANT)\b|\(\s*MAX\s*\)", cdef, re.I):
        return f"explicit source-engine column type \"{cdef}\" in the mapping — remove or align to {target_type}"
    return None
