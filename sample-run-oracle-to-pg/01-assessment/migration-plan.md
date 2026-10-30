# Migration plan — DEMO → demo (Aurora PostgreSQL 18.6)

**Inventory** (`inventory.md`, `inventory-DEMO.yaml`): 14 user tables, 30 indexes, 12 identity sequences,
5 functions, 5 procedures, 5 packages (spec + body), 1 trigger, 0 views; 199 rows. Datatypes: NUMBER 52,
VARCHAR2 44, TIMESTAMP(6) 21, DATE 5, BLOB 1. Engine-internal objects excluded automatically: 4 `DR$` tables
+ 3 `DR$` indexes (Oracle Text).

## Compatibility assessment

| Category | Items | Guidance (playbook file) |
|---|---|---|
| Automatic | tables, B-tree indexes, PK/UNIQUE/CHECK, FKs, identity columns (`GENERATED … AS IDENTITY`) | `target-baseline-aurora-postgresql-18.md` (Conversion defaults); `tables-indexes/common-data-types.md`; `sql-plsql/identity-columns-and-serial.md` |
| Assisted | 5 packages → flattened `<pkg>_<subprogram>` | `sql-plsql/procedures-and-functions.md`; `engines/oracle-to-postgresql/checks/package-naming.md` |
| Assisted | 2 PIPELINED functions (`reporting_pkg`) → `RETURNS TABLE`, column types from the converted columns | `sql-plsql/user-defined-functions.md` |
| Assisted | 5 procedures → `CREATE PROCEDURE` (PG 14+ OUT params); `COMMIT` in 4 procedures removed (caller owns the transaction) | `sql-plsql/procedures-and-functions.md`; `sql-plsql/transaction-model.md` |
| Assisted | `RAISE_APPLICATION_ERROR` (2) → `RAISE EXCEPTION … USING ERRCODE` | `sql-plsql/procedures-and-functions.md` |
| Assisted | `%TYPE` (10), `NVL` (11), `SYSDATE` (4), `REGEXP_*` (2, native since PG 15), `TABLE OF` (1), `DBMS_*` (1) | `sql-plsql/single-row-and-aggregate-functions.md`; `sql-plsql/collections-and-bulk-operations.md` |
| Manual (decision) | **`fulltext_redesign`** — `BOOKS_TEXT_IDX` (`CTXSYS.CONTEXT` on `SEARCH_TEXT`) → tsvector + GIN; app counterpart: `CONTAINS/SCORE` in `BookRepository` | `special-features/` index; `engines/oracle-to-postgresql/checks/non-portable-constructs.md` |
| Blocked | none | — |

**Decision (carried from the previous run of this sample):** Option A — tsvector + GIN on
`to_tsvector('english', coalesce(search_text,''))`; keep the `search_text` maintenance trigger.

**PG 18 defaults to apply** (baseline, verified on 18.6): `VIRTUAL` is the default for generated columns
(none in DEMO); native `MERGE` (not used in DEMO); `uuidv7()` available (no `SYS_GUID` in DEMO).
The previous sample (17.7) needed none of these, so the converted DDL is expected to be close to it.

## Order (units of work)
tables (pre-data) → code → data → FKs + trigger (post-data) → reconcile → equivalence tests → identity reset.

## Testing
Data path `framework`. Semantic tests (`engines/oracle-to-postgresql/checks/equivalence-spec.md` and the
baseline's "Behavior differences" section): empty-string/NULL concatenation, DATE → `timestamp(0)`, 0/1 flags,
SRF column types, NO_DATA_FOUND, rounding.

## Cutover
Big-bang for the sample (dev/test); details in Operations.

## Open questions
None — the full-text decision is carried from the previous sample; gates are pre-approved for this test run.
