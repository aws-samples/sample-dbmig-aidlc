# Migration plan — dbo → dbo

Inventory: 20 tables (2,963 rows), 4 views, 7 functions, 14 procedures. Datatypes: nvarchar 70, int 61,
datetime2 20, datetime 16, nchar 9, decimal 8, numeric 7, bit 6, date 4, smallint 4, varchar 3, xml 3,
uniqueidentifier 2, money 2.

| Category | Items |
|---|---|
| Automatic | tables, PK/FK/UNIQUE, identity, most CHECKs, B-tree indexes |
| Assisted | 7 result-set/cursor procedures → set-returning functions (call-shape change for callers); TRY/CATCH + ambient `ERROR_*()` → `EXCEPTION` + passed diagnostics (`usplogerror` signature changes); `#temp` tables → CTEs; `TOP n PERCENT`; `CHOOSE`; `FORMATMESSAGE`; `money` → `numeric(19,4)`; `datetime` tick rounding |
| Manual (decision) | **`case_insensitive_collation`** — 82 string columns are `_CI_`; PostgreSQL compares case-sensitively. **Decision (recommended, applied, needs owner sign-off):** option (a) `citext` on the columns the application searches (`book.name/author/isbn`, `referencedata.text`, `offer.author/bookname`); other columns case-sensitive (flagged) |
| Manual | 2 CHECKs using `getdate()` (not IMMUTABLE) → static CHECK + trigger; `vwopencoupons` filters on `CURRENT_USER` (DB user vs login — behavioural) |
