# App-layer SQL rules — SQL Server → PostgreSQL

Rules for SQL **embedded in application code**. Schema and stored-code conversion belongs to the
construction phase.

**Mechanical** = dialect syntax, convert directly. **Behavioural** = compiles and runs but can
return different results — convert **and** raise it in the change plan.

---

## 1. Mechanical rewrites

| SQL Server | PostgreSQL | Note |
|---|---|---|
| `GETDATE()` / `SYSDATETIME()` | `CURRENT_TIMESTAMP` / `LOCALTIMESTAMP` | |
| `GETUTCDATE()` | `now() AT TIME ZONE 'UTC'` | |
| `ISNULL(a,b)` | `COALESCE(a,b)` | |
| `a + b` (strings) | `a \|\| b` | **`+` on text is addition in PG** — see §2 |
| `LEN(x)` | `length(x)` | `LEN` ignores trailing spaces — see §2 |
| `TOP n` | `LIMIT n` | `TOP n WITH TIES` → `FETCH FIRST n ROWS WITH TIES` |
| `TOP n PERCENT` | CTE with a computed `LIMIT` | |
| `CONVERT(type, x)` / `CAST` | `CAST(x AS type)` / `x::type` | `CONVERT` style codes have no equivalent |
| `DATEADD(day,n,d)` | `d + n * INTERVAL '1 day'` | |
| `DATEDIFF(day,a,b)` | `(b::date - a::date)` | see §2 for other units |
| `DATEPART(yy,d)` | `EXTRACT(YEAR FROM d)` | |
| `FORMAT(d,'yyyy-MM')` | `to_char(d,'YYYY-MM')` | mask syntax differs |
| `NEWID()` | `gen_random_uuid()` | |
| `IDENTITY`/`SCOPE_IDENTITY()` | `RETURNING id` / `getGeneratedKeys()` | |
| `OUTPUT INSERTED.*` | `RETURNING *` | |
| `CROSS APPLY` / `OUTER APPLY` | `CROSS JOIN LATERAL` / `LEFT JOIN LATERAL … ON true` | |
| `STUFF(...FOR XML PATH)` idiom | `string_agg(x, d ORDER BY y)` | |
| `CHARINDEX(a,b)` | `position(a IN b)` | |
| `SUBSTRING/REPLACE/UPPER` | same names | |
| `IIF(c,a,b)` | `CASE WHEN c THEN a ELSE b END` | |
| `WITH (NOLOCK)` | remove | MVCC makes it unnecessary — see §2 |
| `MERGE` | `INSERT … ON CONFLICT DO UPDATE` | native `MERGE` exists in PG 15+ |
| `[bracketed]` identifiers | `"quoted"` or unquoted lower case | prefer unquoted lower |
| `@name` binds | `:name` (JDBC/JPA) or `$n`/`%s` | see §2 |

---

## 2. Behavioural differences — convert AND flag

- **`+` for string concatenation.** In PostgreSQL `+` on text raises `operator does not exist`
  (a loud failure — good) but on numeric-looking text it may coerce and *add*. Always rewrite to
  `||`, and remember `||` propagates NULL whereas SQL Server's `+` depends on
  `CONCAT_NULL_YIELDS_NULL`. Use `concat()` or `COALESCE` to match the source behaviour.
- **Case-insensitive comparisons.** SQL Server's default collation is usually
  **case-insensitive** (`SQL_Latin1_General_CP1_CI_AS`), PostgreSQL is **case-sensitive**. Every
  `WHERE name = 'abc'` that used to match `'ABC'` now does not. This silently shrinks result sets
  and is the most consequential behavioural difference in this pair. Fix with `lower()` on both
  sides, `citext`, or an explicit collation — and flag every occurrence.
- **`LEN` vs `length`.** `LEN` ignores trailing spaces; `length` does not. Comparisons and
  validation on `char`-padded columns change.
- **`DATEDIFF` counts boundaries, not elapsed time.** `DATEDIFF(day,'2026-01-01 23:00','2026-01-02 01:00')`
  is 1 in SQL Server, while `(b::date - a::date)` is also 1 — but for `month`/`year` the boundary
  semantics differ from any simple subtraction. Convert each unit deliberately.
- **`TOP n` without `ORDER BY`** is non-deterministic in both engines, but the *chosen* rows will
  differ. If a test or UI depends on the order, add an explicit `ORDER BY`.
- **`WITH (NOLOCK)`** is not a no-op semantically: it permitted dirty reads. Removing it makes
  reads consistent — usually a correctness improvement, but it can change what a report returns
  and can increase contention. Flag rather than silently drop.
- **Implicit conversion.** SQL Server coerces across types using datatype precedence;
  PostgreSQL refuses. Add explicit casts, and note that `CAST(textcol AS numeric)` now *errors* on
  dirty data SQL Server tolerated — a data-quality question.
- **`bit` → `boolean`.** If the migration mapped `bit` to `boolean`, code binding `0`/`1` or
  comparing `= 1` must switch to `true`/`false`. Check the conversion log for which mapping was used.
- **`COUNT(*)` is `bigint`** — widen the receiving type.
- **Result-set column case.** SQL Server preserves PascalCase; PostgreSQL folds to lower.
  `reader["OrderId"]` / `rs.getX("OrderId")` breaks at runtime while compiling fine. Alias
  explicitly in SQL, or lower-case the keys.
- **`money`/`datetime` precision.** `money` → `numeric(19,4)`; `datetime` rounds to ~3.33 ms ticks
  whereas `timestamp` is exact, so equality assertions on datetimes may fail.

---

## 3. Full-text search

| SQL Server (app code) | PostgreSQL |
|---|---|
| `CONTAINS(col, :terms)` | `to_tsvector('english', coalesce(col,'')) @@ to_tsquery('english', :terms)` |
| `FREETEXT(col, :terms)` | `… @@ plainto_tsquery('english', :terms)` |
| `CONTAINSTABLE(...)` / `FREETEXTTABLE(...)` with `RANK` | join to the query and order by `ts_rank(...)` |

- SQL Server's `CONTAINS` accepts `AND`/`OR`/`NEAR`/prefix `"word*"`; `to_tsquery` needs `&`, `|`,
  `!`, `<->` and **rejects bare spaces**. For a free-text UI field use `plainto_tsquery` or
  `websearch_to_tsquery` (which never raises) rather than `to_tsquery`.
- `FREETEXT` maps naturally to `plainto_tsquery`.
- `RANK` from `CONTAINSTABLE` and `ts_rank` are not comparable in magnitude.
- The GIN index expression must match the query expression exactly or the planner falls back to a
  sequential scan — verify with `EXPLAIN`.

---

## 4. Stored-routine call sites

- **`EXEC p @a = ?` → `CALL p(?)`** (procedure) or `SELECT * FROM f(?)` (if converted to a
  function). JDBC `{ call p(?) }` works for procedures.
- **Result-set procedures.** A SQL Server procedure returning rows via a trailing `SELECT` has no
  direct PostgreSQL procedure equivalent; the migration typically converts it to
  `RETURNS TABLE(...)`. Call sites change from `EXEC`/`CommandType.StoredProcedure` to a normal
  query — a caller contract change.
- **Multiple result sets** from one procedure need redesign (several functions, or a refcursor per
  set).
- **Table-valued parameters** have no equivalent: bind an array of a composite type
  (`unnest($1)`), or send `jsonb` and expand with `jsonb_to_recordset`. Any client code building a
  `DataTable`/`SqlParameter` with `SqlDbType.Structured` must be rewritten.
- **`OUTPUT` parameters** still work via `CallableStatement`, but a routine converted to
  `RETURNS TABLE` must be consumed as a result set.

---

## 5. ORM / framework specifics

- **Hibernate dialect** → `PostgreSQLDialect`; **EF Core** provider → `UseNpgsql(...)` replacing
  `UseSqlServer(...)`, plus the `Npgsql.EntityFrameworkCore.PostgreSQL` package.
- **EF Core quotes PascalCase — fold the model, not the queries.** EF emits quoted identifiers
  from entity/property names (`SELECT "b"."Id" FROM "Book"`), so a pure-LINQ app fails with
  `42P01 relation "Book" does not exist` against a lower-cased migrated schema even though it
  compiles cleanly. Fix once in `OnModelCreating` rather than per query:

  ```csharp
  foreach (var entity in modelBuilder.Model.GetEntityTypes())
  {
      entity.SetTableName(entity.GetTableName()?.ToLowerInvariant());
      foreach (var p in entity.GetProperties())
          p.SetColumnName(p.GetColumnBaseName().ToLowerInvariant());
  }
  ```
  Verified against a live target on a real EF Core 8 app: with the fold, `DbSet` queries,
  `Include` joins and the reserved-word `"order"` table all resolve.
- **Check `ToTable`/`DbSet` names against the SOURCE catalog during inventory.** A real app
  mapped `Order` → `ToTable("Orders")` while the source table was `Order` (singular) —
  pre-existing model/DB drift the migration surfaces. Conform the mapping to the *migrated*
  table and flag the drift; do not assume the EF model matches the source.
- **Connection string is built in code more often than read from config.** Look for
  `SqlConnectionStringBuilder` (→ `NpgsqlConnectionStringBuilder`: `Host`/`Port`/`Database`/
  `SearchPath`/`SslMode`), not just `appsettings.json`. SQL Server's
  `Initial Catalog`/`MultipleActiveResultSets`/`TrustServerCertificate` have no Npgsql
  equivalents — MARS in particular simply disappears; concurrent readers on one connection
  need restructuring, not renaming.
- **EF Core migrations** are provider-specific: existing SQL Server migration files will not apply
  to PostgreSQL. Do not attempt to convert migration history — flag it, and plan to baseline
  against the migrated schema.
- **`@Table(schema="dbo")`** → the target schema name (often lower case). `dbo` rarely survives.
- **Bracketed identifiers** `[Order]` must become `"order"` (a reserved word) or be renamed.
- **`ddl-auto` / `EnsureCreated`** — keep off; never let the ORM alter a migrated schema.
- **Dapper** `@name` parameters are generally translated by Npgsql, but verify; raw
  `NpgsqlCommand` text needs `:name` or `$n`.

---

## 6. Not converted by this module

In-database stored procedures/functions and schema DDL (construction phase), SQL Agent jobs, SSIS
packages and CLR assemblies (flag — they need re-platforming, not conversion).
