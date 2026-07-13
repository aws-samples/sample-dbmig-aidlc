# Equivalence Testing Spec — SQL Server → PostgreSQL

Same methodology as the framework's other pairs, adapted to SQL Server source.
The validation phase proves the converted target behaves like the source:
*same input → same value (functions) / same net effect (procedures/DML)*.
`dbmig run-tests` executes each case on both engines inside a transaction that is
**rolled back** afterward.

## 1. Data reconciliation (table level)
- Row counts per table (`dbmig compare`) must match exactly.
- Numeric aggregates compared within tolerance; hashing algorithms differ between
  SQL Server (`CHECKSUM_AGG`) and PostgreSQL (`md5`), so prefer aggregate + keyed-sample
  comparison for value-level equivalence (see reconcile.sql.tmpl).

## 2. Function parity (same input → same return value)
- SQL Server: `SELECT [schema].[fn](@a);`   PostgreSQL: `SELECT schema.fn(:a);`
- Build the input matrix from real data (typical, boundary, NULL, empty-string).
- Compare the scalar return within `float_tolerance`; normalize whitespace.

## 3. Procedure parity (same input → same net effect)
- Snapshot probe queries before/after the call on each engine; compare the delta.
- SQL Server call: `EXEC [schema].[proc] @a;`   PostgreSQL call: `CALL schema.proc(:a);`
- Compare affected-row counts, resulting table state, OUT params, and IDENTITY/sequence
  advancement.

## 4. Known semantic differences to assert explicitly
- **Case sensitivity**: SQL Server is usually case-insensitive (collation-dependent);
  PostgreSQL is case-sensitive. Test string equality/`LIKE`/ORDER BY; consider `citext`
  or `lower()`.
- **Empty string vs NULL**: both treat `''` as not NULL (unlike Oracle), but watch
  `ISNULL`→`COALESCE` and concatenation with NULL.
- **IDENTITY / SCOPE_IDENTITY()**: maps to `GENERATED AS IDENTITY` / `RETURNING` /
  `currval` — verify generated keys.
- **Dates**: `GETDATE()`→`now()`, `DATEADD/DATEDIFF`→interval arithmetic; `datetime`
  rounding (~3.33 ms) vs `timestamp`.
- **rowversion/timestamp** is a binary row-version, NOT a datetime.
- **MERGE**: native in PostgreSQL 15+, else `INSERT ... ON CONFLICT`.
- **TOP n** → `LIMIT`; `+` string concat → `||`; `LEN`→`length`, `CHARINDEX`→`position`.
- **Booleans**: SQL Server `bit` (0/1) vs PostgreSQL `boolean` — verify comparisons.

## 5. Reporting
`run-tests` writes `03-validation/equivalence-report.yaml` (+ `.md`); failures are recorded
to the project follow-up log (silent mode) or prompted (interactive mode), and link back to
the converted object and the relevant `sqlserver-to-postgresql-playbook` reference.

## 6. Transaction caveat
A stored procedure that issues its own `COMMIT`, or T-SQL DDL, cannot be rolled back —
flag such procedures and test them only against a disposable target.
