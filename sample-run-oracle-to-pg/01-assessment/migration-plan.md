# Migration plan — DEMO → demo

**Inventory** (`inventory-DEMO.yaml`): 14 user tables, 30 indexes, 12 identity sequences, 5 functions,
5 procedures, 5 packages (spec + body), 1 trigger, 0 views. Datatypes: NUMBER 52, VARCHAR2 44,
TIMESTAMP(6) 21, DATE 5, BLOB 1. Engine-internal objects excluded automatically: 4 `DR$` tables +
3 `DR$` indexes (Oracle Text). 199 rows.

| Category | Items |
|---|---|
| Automatic | tables, B-tree indexes, PK/UNIQUE/CHECK, FKs, identity columns |
| Assisted | 5 packages → flattened `<pkg>_<subprogram>`; PIPELINED `get_top_books` → `RETURNS TABLE`; OUT-param procedures; `RAISE_APPLICATION_ERROR` → `RAISE … ERRCODE 'U00nn'`; `COMMIT` in 4 procedures removed (caller owns txn) |
| Manual (decision) | **`fulltext_redesign`** — `BOOKS_TEXT_IDX` (`CTXSYS.CONTEXT` on `SEARCH_TEXT`) → tsvector + GIN; app counterpart: `CONTAINS/SCORE` in `BookRepository` |
| Blocked | none |

**Decision taken:** Option A — tsvector + GIN on `to_tsvector('english', coalesce(search_text,''))`,
keep the `search_text` maintenance trigger (it is part of the data model).

**Order:** tables (pre-data) → code → data → FKs + trigger (post-data) → reconcile → equivalence tests
→ identity reset. **Semantic tests:** empty-string/NULL concatenation, DATE→timestamp(0), 0/1 flags,
SRF column types, NO_DATA_FOUND.
