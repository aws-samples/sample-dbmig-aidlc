# Equivalence Testing Spec — Oracle → PostgreSQL

The validation phase proves the **converted target behaves the same as the source**:
*same input → same value (functions) or same net effect (procedures/DML)*. This file
defines the comparison methodology the `db-migration-validation` skill follows.

## 1. Data reconciliation (table level)

| Check | Method | Pass condition |
|---|---|---|
| Row count | `COUNT(*)` per table both sides | exact match |
| Column checksum | order-independent aggregate hash per column (see `reconcile.sql.tmpl`) | match after normalization |
| Numeric aggregates | MIN/MAX/AVG/SUM per numeric column | match within `float_tolerance` |
| Keyed sample | N rows by PK, compared column-by-column | match after normalization |

## 2. Query parity

For each representative `SELECT` (from views, reports, or app queries):

1. Run on Oracle and PostgreSQL with identical bind values.
2. Normalize result sets before comparing:
   - sort rows if `sort_unordered_results` (no ORDER BY in the query),
   - trim/collapse whitespace if `normalize_whitespace`,
   - compare floats within `float_tolerance`,
   - treat Oracle `''` (NULL) vs PG `''` explicitly — **known semantic difference**.
3. Pass = normalized result sets are identical.

## 3. Function parity (same input → same return value)

For each converted function:

1. Build a test-input matrix: typical values, boundary values, NULLs, and known
   edge cases (empty string, max length, negative, zero).
2. Call the function on both engines for each input row.
3. Compare the scalar return value (tolerance/normalization as above).
4. Record per-input pass/fail; any mismatch fails the function.

Example harness shape:
```
-- Oracle:   SELECT my_fn(:a, :b) FROM dual;
-- Postgres: SELECT my_fn(:a, :b);
```

## 4. Procedure / DML parity (same input → same net effect)

Procedures rarely "return" a value — they change state. Compare the **net effect**:

1. Snapshot affected tables on both sides (row count + checksum) **before**.
2. Execute the procedure with identical inputs on both engines, in a transaction.
3. Capture: rows inserted/updated/deleted, output params, sequence/identity advance,
   and raised errors/exceptions.
4. Snapshot **after**; the delta (post − pre) must match between engines.
5. Roll back (test isolation) unless the run is an explicit destructive test.

Net-effect dimensions compared:
- affected-row counts per table,
- post-state checksums of affected tables,
- OUT/INOUT parameter values,
- error/exception raised (same logical error, mapped Oracle↔PG SQLSTATE),
- side effects (sequence currval advance, audit rows).

## 5. Reporting

Each object gets a row in the validation report:

```
object_type | object_name | check | status(PASS/FAIL/SKIP) | detail | playbook_ref
```

`playbook_ref` points to the relevant
`oracle-to-postgresql-playbook/references/...` topic so a failure links straight to the
conversion guidance that explains the difference (e.g. NULL/empty-string handling,
date arithmetic, implicit casts).

## 6. Known semantic differences to assert explicitly

These are *expected* to differ if not handled — the harness checks them on purpose:

- Empty string `''` is NULL in Oracle but not in PostgreSQL.
- `DATE` arithmetic: Oracle `date+1` = +1 day; PG uses `interval`.
- Default numeric rounding (`NUMBER` vs `numeric`/`double precision`).
- Implicit type coercion is more permissive in Oracle.
- `ROWNUM` vs `LIMIT`/window functions ordering.
- Case-insensitive identifier folding (Oracle UPPER vs PG lower).
- Transaction/DDL autocommit behavior differences.
