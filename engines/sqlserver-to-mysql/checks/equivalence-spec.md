# Equivalence Testing Spec — SQL Server → MySQL

Same methodology as the framework's other pairs, adapted to a SQL Server source and a MySQL
(Aurora MySQL) target. The validation phase proves the converted target behaves like the
source: *same input → same value (functions) / same net effect (procedures/DML)*.
`dbmig run-tests` executes each case on both engines inside a transaction that is **rolled
back** afterward.

## 1. Data reconciliation (table level)
- Row counts per table (`dbmig compare`) must match exactly.
- Numeric aggregates compared within tolerance; hashing differs between SQL Server
  (`CHECKSUM_AGG`) and MySQL (`MD5`), so prefer aggregate + keyed-sample comparison
  (see reconcile.sql.tmpl). Reminder: a MySQL *schema* is a *database*.

## 2. Function parity (same input → same return value)
- SQL Server: `SELECT [schema].[fn](@a);`   MySQL: `SELECT schema.fn(:a);`
- Build the input matrix from real data (typical, boundary, NULL, empty-string).
- Compare the scalar return within `float_tolerance`; normalize whitespace.

## 3. Procedure parity (same input → same net effect)
- Snapshot probe queries before/after the call on each engine; compare the delta.
- SQL Server call: `EXEC [schema].[proc] @a;`   MySQL call: `CALL schema.proc(:a);`
- Compare affected-row counts, resulting table state, OUT params, and AUTO_INCREMENT
  advancement.

## 4. Known semantic differences to assert explicitly
- **Case sensitivity**: SQL Server usually case-insensitive (collation-dependent); MySQL
  depends on collation + `lower_case_table_names`. Choose a MySQL collation matching the app
  (e.g. `utf8mb4_0900_ai_ci`) and verify string comparisons.
- **IDENTITY → AUTO_INCREMENT** (one per table); `SCOPE_IDENTITY()`/`@@IDENTITY` →
  `LAST_INSERT_ID()`.
- **Dates**: `GETDATE()`→`NOW()`, `DATEADD/DATEDIFF`→`DATE_ADD`/`TIMESTAMPDIFF`; `datetime`
  rounding (~3.33 ms) vs `datetime(3)`.
- **rowversion/timestamp** is a binary row-version, NOT a datetime.
- **No MERGE** → `INSERT ... ON DUPLICATE KEY UPDATE`; verify upsert outcomes.
- **bit vs tinyint(1)**; `TOP n`→`LIMIT`; `+` concat→`CONCAT()`; `LEN`→`CHAR_LENGTH`;
  `ISNULL`→`IFNULL`/`COALESCE`; `CHARINDEX`→`LOCATE`.
- **No equivalent / redesign**: CLR, Service Broker, linked servers (use FEDERATED/app),
  full-text search (MySQL FULLTEXT differs), columnstore, `hierarchyid`, `sql_variant`.

## 5. Reporting
`run-tests` writes `03-validation/equivalence-report.yaml` (+ `.md`); failures are recorded
to the project follow-up log (silent mode) or prompted (interactive mode), and link back to
the converted object and the relevant `sqlserver-to-mysql-playbook` reference.

## 6. Transaction caveat
MySQL DDL causes an implicit commit, and a stored procedure that issues `COMMIT` cannot be
rolled back — flag such procedures and test them only against a disposable target.
