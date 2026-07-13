# Equivalence Testing Spec — Oracle → MySQL

Same methodology as the framework's PostgreSQL spec, adapted to MySQL/Aurora
MySQL. The validation phase proves the converted target behaves like the source:
*same input → same value (functions) / same net effect (procedures/DML)*.
`dbmig run-tests` executes each case on both engines inside a transaction that is
**rolled back** afterward.

## 1. Data reconciliation (table level)
- Row counts per table (`dbmig compare`) must match exactly.
- Column checksums / aggregates compared within tolerance (see reconcile.sql.tmpl).
- Reminder: a MySQL *schema* is a *database*; the Oracle schema maps to a MySQL database.

## 2. Function parity (same input → same return value)
- Oracle: `SELECT app.fn(:a) FROM dual;`  MySQL: `SELECT app.fn(:a);`
- Build the input matrix from real data (typical, boundary, NULL, empty-string).
- Compare the scalar return within `float_tolerance`; normalize whitespace.

## 3. Procedure / DML parity (same input → same net effect)
- Snapshot probe queries before/after the call on each engine; compare the delta.
- Oracle call: `BEGIN app.proc(:a); END;`  MySQL call: `CALL app.proc(:a);`
- Compare affected-row counts, resulting table state, OUT params, and AUTO_INCREMENT
  advancement.

## 4. Known semantic differences to assert explicitly
- Empty string `''` is NULL in Oracle but **not** in MySQL.
- `DATE` arithmetic: Oracle `date+1` = +1 day; MySQL uses `DATE_ADD(d, INTERVAL 1 DAY)`.
- Sequences: Oracle sequences → MySQL `AUTO_INCREMENT` (one per table). Logic relying on
  multiple/shared sequences or `seq.NEXTVAL` mid-statement needs redesign — test carefully.
- No `MERGE`: converted as `INSERT ... ON DUPLICATE KEY UPDATE` — verify upsert outcomes.
- `GROUP BY` strictness (`only_full_group_by`) and implicit casts differ from Oracle.
- `ROWNUM`/hierarchical queries (`CONNECT BY`) → `LIMIT` / recursive CTE (MySQL 8) — verify.
- TIMESTAMP WITH TIME ZONE has no native MySQL type — verify tz handling.
- Number rounding: Oracle `NUMBER` vs MySQL `DECIMAL`/`DOUBLE`.

## 5. Reporting
`run-tests` writes `03-validation/equivalence-report.yaml` (+ `.md`); failures are recorded
to the project follow-up log (silent mode) or prompted (interactive mode), and link back to
the converted object and the relevant `oracle-to-mysql-playbook` reference.

## 6. Transaction caveat
MySQL DDL statements cause an **implicit commit**, and a stored procedure that issues `COMMIT`
cannot be rolled back. Flag such procedures and test them only against a disposable target.
