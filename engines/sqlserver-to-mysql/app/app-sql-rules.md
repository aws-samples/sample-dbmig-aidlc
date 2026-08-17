# App-layer SQL rules — SQL Server → MySQL

Rules for SQL **embedded in application code**. Schema and stored-code conversion belongs to the
construction phase.

**Mechanical** = dialect syntax, convert directly. **Behavioural** = compiles and runs but can
return different results — convert **and** raise it in the change plan.

---

## 1. Mechanical rewrites

| SQL Server | MySQL | Note |
|---|---|---|
| `GETDATE()` / `SYSDATETIME()` | `NOW()` / `NOW(6)` | |
| `GETUTCDATE()` | `UTC_TIMESTAMP()` | |
| `ISNULL(a,b)` | `IFNULL(a,b)` | |
| `a + b` (strings) | `CONCAT(a,b)` | **`+` adds numerically in MySQL** — see §2 |
| `LEN(x)` | `CHAR_LENGTH(x)` | `LENGTH` is bytes in MySQL |
| `TOP n` | `LIMIT n` | |
| `TOP n PERCENT` | computed `LIMIT` | |
| `CONVERT(type,x)` / `CAST` | `CAST(x AS type)` | `CONVERT` style codes have no equivalent |
| `DATEADD(day,n,d)` | `DATE_ADD(d, INTERVAL n DAY)` | |
| `DATEDIFF(day,a,b)` | `DATEDIFF(b,a)` (days) / `TIMESTAMPDIFF(unit,a,b)` | **argument order reverses** — see §2 |
| `DATEPART(yy,d)` | `YEAR(d)` / `EXTRACT(YEAR FROM d)` | |
| `FORMAT(d,'yyyy-MM')` | `DATE_FORMAT(d,'%Y-%m')` | mask language differs |
| `NEWID()` | `UUID()` | |
| `SCOPE_IDENTITY()` | `LAST_INSERT_ID()` | |
| `OUTPUT INSERTED.id` | insert, then `LAST_INSERT_ID()` | no OUTPUT clause |
| `CROSS APPLY` / `OUTER APPLY` | `JOIN LATERAL` (8.0.14+) or rewritten join | |
| `STUFF(...FOR XML PATH)` idiom | `GROUP_CONCAT(x ORDER BY y SEPARATOR d)` | `group_concat_max_len` |
| `CHARINDEX(a,b)` | `INSTR(b,a)` | **argument order reverses** |
| `IIF(c,a,b)` | `IF(c,a,b)` | |
| `WITH (NOLOCK)` | remove | see §2 |
| `MERGE` | `INSERT … ON DUPLICATE KEY UPDATE` | |
| `[bracketed]` identifiers | `` `backticked` `` | |
| `@name` binds | `?` positional | see §2 — do not leave `@name` |
| `EXCEPT` / `INTERSECT` | 8.0.31+ native, else `LEFT JOIN`/`IN` | |

---

## 2. Behavioural differences — convert AND flag

- **`@name` left in place becomes a session variable, not a bind.** MySQL treats `@x` as a
  user-defined variable; if a find/replace misses one, the query reads an unset variable (NULL)
  rather than failing. Silent wrong results — check every parameter after conversion.
- **`+` on strings.** SQL Server concatenates; MySQL performs numeric addition, so
  `'a' + 'b'` yields `0` and `'1' + '2'` yields `3`. No error. Always rewrite to `CONCAT`, and note
  `CONCAT` returns NULL if any argument is NULL (use `IFNULL`).
- **`DATEDIFF` and `CHARINDEX` reverse their argument order.** A copied call compiles and returns a
  plausible-but-wrong value (often the negation). Check each one individually.
- **Case sensitivity flips twice — check carefully.** SQL Server's default collation is
  case-**insensitive**; MySQL's common `utf8mb4_0900_ai_ci` is also case-insensitive, so string
  comparisons often behave the same. But **identifier/table-name** case sensitivity depends on
  `lower_case_table_names` and the filesystem, so an app developed against Windows SQL Server can
  break on Linux MySQL. Standardise on lower case.
- **`DATEDIFF` counts boundaries** in SQL Server; MySQL's `DATEDIFF` returns whole days between
  dates. For month/year units use `TIMESTAMPDIFF` and verify the boundary semantics.
- **`LEN` ignores trailing spaces**, `CHAR_LENGTH` does not — validation and comparisons on
  `char`-padded columns change.
- **`WITH (NOLOCK)`** permitted dirty reads; removing it makes reads consistent. Usually a
  correctness improvement, but it can change what a report returns. Flag, don't silently drop.
- **Implicit conversion in both, with different rules.** MySQL converts a non-numeric string to
  `0` in numeric context. A mismatched comparison that "worked" can return *different rows* with no
  diagnostic. Add explicit casts and treat as data quality.
- **`GROUP BY` strictness.** MySQL 8.0 enables `ONLY_FULL_GROUP_BY`, rejecting queries SQL Server
  accepted. That failure is loud, but the fix (`ANY_VALUE`, or adding columns) can change results.
- **Sort order / NULL placement.** MySQL sorts NULLs first ascending; SQL Server also sorts NULLs
  first — but collation-driven ordering of mixed case/accents differs. Add explicit ordering where
  it is contractual.
- **`COUNT(*)` is BIGINT** — widen the receiving type.
- **`money`/`datetime2` precision.** `money` → `decimal(19,4)`; `datetime2(7)` exceeds MySQL's
  maximum `datetime(6)`, so the 7th fractional digit is **lost** — flag if precision matters.
- **Multi-row insert + `LAST_INSERT_ID()`** returns only the first generated id, unlike an `OUTPUT`
  clause that returned all of them. Batch-insert code that captured every id must be redesigned.

---

## 3. Full-text search

| SQL Server (app code) | MySQL |
|---|---|
| `CONTAINS(col, :terms)` | `MATCH(col) AGAINST(:terms IN BOOLEAN MODE)` |
| `FREETEXT(col, :terms)` | `MATCH(col) AGAINST(:terms IN NATURAL LANGUAGE MODE)` |
| `CONTAINSTABLE`/`FREETEXTTABLE` with `RANK` | `ORDER BY MATCH(col) AGAINST(:terms …) DESC` |

- A `FULLTEXT` index must exist, and `MATCH` must list **exactly** the indexed columns.
- `innodb_ft_min_token_size` defaults to **3**, so shorter terms silently return nothing.
- SQL Server `NEAR` and weighted terms have no MySQL equivalent — redesign or drop, and flag.
- Relevance values are not comparable to SQL Server `RANK`.

---

## 4. Stored-routine call sites

- `EXEC p @a = ?` → `CALL p(?)`. MySQL procedures return result sets naturally, so
  result-set procedures port more directly than they do to PostgreSQL.
- **No table-valued parameters**: send JSON (`JSON_TABLE`, 8.0+) or populate a temporary table
  before the call. `SqlDbType.Structured` / `DataTable` client code must be rewritten.
- **No parameter defaults** — callers must pass every argument.
- **Multiple result sets** are supported by MySQL, but the driver's API for iterating them differs.
- **Transaction ownership** where an internal transaction was removed.

---

## 5. ORM / framework specifics

- **Hibernate dialect** → `MySQLDialect`; **EF Core** → `UseMySql(...)` with Pomelo or the Oracle
  MySQL provider, replacing `UseSqlServer(...)`.
- **Pomelo pins its own EF Core floor — align versions or NU1605 fails the build.** Pomelo 8.0.3
  requires EF Core ≥ 8.0.13; a project pinning EF 8.0.11 hits
  `NU1605 Detected package downgrade`. Raise the app's EF packages to Pomelo's floor (all of
  them — Design/Tools/other providers too). Also pass an explicit
  `ServerVersion.Create(...)` rather than `AutoDetect` in environments where the DB is not
  reachable at startup-time configuration.
- **EF Core quotes PascalCase — fold the model in `OnModelCreating`** (same
  `SetTableName`/`SetColumnName` lower-case loop as the PostgreSQL pair; verified live against
  Aurora MySQL). This also insulates against `lower_case_table_names` differences on Linux.
- **Check `ToTable`/`DbSet` names against the SOURCE catalog during inventory** — a real app
  mapped `Order` → `ToTable("Orders")` while the source table was `Order`; conform to the
  migrated table and flag the drift.
- **Connection string built in code:** `SqlConnectionStringBuilder` →
  `MySqlConnectionStringBuilder` (`Server`/`Port` is `uint`/`Database`/`SslMode`).
  `Initial Catalog` → `Database`; `MultipleActiveResultSets` has no equivalent (MARS-dependent
  code needs restructuring); the schema=database mapping means `Database` is the migrated
  database derived from the source schema.
- **EF Core migrations are provider-specific** — SQL Server migration files will not apply. Flag
  and baseline against the migrated schema rather than converting history.
- **Schema → database.** `@Table(schema="dbo")` becomes `@Table(catalog="…")`, or the database
  moves into the URL. A source database with several schemas becomes several MySQL databases, so
  cross-schema joins become cross-database and the default database must be chosen deliberately.
- **`@GeneratedValue`** → `GenerationType.IDENTITY` for `AUTO_INCREMENT`.
- **Bracketed identifiers** `[Order]` → backticks; `order` is reserved.
- **`serverTimezone`** must be set explicitly or timestamps shift.
- **`ddl-auto` / `EnsureCreated`** — keep off.

---

## 6. Not converted by this module

In-database routines and schema DDL (construction phase); SQL Agent jobs, SSIS packages and CLR
assemblies (flag — they need re-platforming).
