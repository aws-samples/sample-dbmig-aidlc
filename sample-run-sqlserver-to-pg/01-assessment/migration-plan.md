# Migration plan — dbo → dbo (Aurora PostgreSQL 18.6)

Inventory: 20 tables (2,963 rows), 4 views, 7 functions, 14 procedures. Datatypes: nvarchar 70, int 61,
datetime2 20, datetime 16, nchar 9, decimal 8, numeric 7, bit 6, date 4, smallint 4, varchar 3, xml 3,
uniqueidentifier 2, money 2.

| Category | Items | Guidance |
|---|---|---|
| Automatic | tables, PK/FK/UNIQUE, identity, most CHECKs, B-tree indexes | `references/target-baseline-aurora-postgresql-18.md` (Conversion defaults) |
| Assisted | 7 result-set/cursor procedures → set-returning functions (call-shape change); TRY/CATCH + `ERROR_*()` → `EXCEPTION` + passed diagnostics; `#temp` → CTEs; `TOP n PERCENT`; `CHOOSE`; `FORMATMESSAGE`; `money` → `numeric(19,4)`; `datetime` tick rounding | `tsql/stored-procedures.md`, `tsql/error-handling.md`, `tsql/top-fetch.md` |
| Assisted (new on PG 18 baseline) | unique index over a nullable column (`AK_BillOfMaterials_…`) → `NULLS NOT DISTINCT` to keep SQL Server's one-NULL rule | baseline Conversion defaults |
| Manual (decision) | **`case_insensitive_collation`** — 82 `_CI_` string columns. Decision (carried): `citext` on the searched columns (`book.name/author/isbn`, `referencedata.text`, `offer.author/bookname`); others case-sensitive (flagged). Unique indexes on other CI columns (e.g. `product.name`) become case-sensitive — flagged | `tsql/collations.md`; engine check §17 |
| Manual | 2 CHECKs using `getdate()` → static CHECK + trigger; `vwopencoupons` filters on `CURRENT_USER` (behavioural) | engine check §1 |
| Blocked | none | — |

Order: tables → code → data → FKs/triggers → reconcile → equivalence tests → identity reset.
Behaviour to test (baseline "Behavior differences"): case/trailing-space equality, `LEN`, `CAST` truncation,
`DATEDIFF` boundaries, `datetime` rounding, NULL sort order.
