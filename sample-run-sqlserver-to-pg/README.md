# Sample run — SQL Server `BobsUsedBookStore` → Aurora PostgreSQL (+ .NET EF Core app)

A complete, real run **converted from scratch** by dbmig-aidlc (for the path that *continues from AWS DMS
Schema Conversion*, see [`sample-run-dms-sc-sqlserver-to-pg/`](../sample-run-dms-sc-sqlserver-to-pg/)).
Masked: hosts, account ids, local paths and credentials are placeholders.

- **Source:** SQL Server 2022 (RDS), `BobsUsedBookStore.dbo` (collation `SQL_Latin1_General_CP1_CI_AS`)
- **Target:** Aurora PostgreSQL **18.6**, database `bookstore`, schema `dbo`
- **Refreshed 2026-10-30** on a fresh 18.6 cluster with a SQL Server instance loaded from the workshop scripts (same 20 tables / 2,963 rows), using the refreshed playbooks, the new SQL Server → PG 18 baseline and the context wiring
- **App:** Bob's Used Bookstore .NET (branch `MAM303`), ASP.NET Core + EF Core 8, pure LINQ

## Result at a glance

| Phase | Result |
|---|---|
| Inventory | 20 tables, 4 views, 7 functions, 14 procedures, 2,963 rows; decision item **`case_insensitive_collation`** (82 `_CI_` string columns) |
| Tables / code | **20/20** (17/20 on the first apply — `citext` not on the apply session's search path, fixed by writing `dbo.citext`) and **25/25**; post-data **6/6** |
| Data | **20/20** tables reconcile; identity **14/14** safe |
| Equivalence tests | **69/69** first run — the 68 carried cases plus a full result-set comparison of `uspgetbillofmaterials` (3 rows × 8 columns) |
| App | 4 files (+49/−13); builds; runs against the migrated schema; search (`gold`, `GOLD`, `children of`), details, cart, wishlist, address, 5 admin pages 200 with 0 PostgreSQL errors |
| Traceability | `conversion-log.md` cites **10 distinct playbook topics** |

## Found during this refresh (and fixed in the framework)

- **The SQL Server pair was given the Oracle-oriented PG 18 baseline.** It now has its own,
  `skills/sqlserver-to-postgresql-playbook/references/target-baseline-aurora-postgresql-18.md`, verified on SQL Server
  2022 and 18.6 (CI/trailing-space equality, `LEN`, `CAST` truncation, float `ROUND`, `DATEDIFF`, NULL ordering, unique NULLs).
- **Unique index over a nullable column** (`AK_BillOfMaterials_…`): SQL Server allows one NULL, PostgreSQL many →
  `NULLS NOT DISTINCT` (found from the new baseline).
- **`citext` must be schema-qualified in DDL** on a fresh target (engine check §17 updated). The previous run passed
  only because `citext` was already installed.
- **The original `uspgetbillofmaterials` tests returned 0 rows on both engines** (products 800/750/977 are not
  assemblies in this data), so they proved only the empty path. The new case uses `compare: resultset`, which
  `run-tests` now implements (it was documented but compared only the first value).
- On PostgreSQL 18 an ICU nondeterministic collation also supports `LIKE` (verified) — a viable alternative to
  `citext` for the `case_insensitive_collation` decision; this run kept `citext` (owner decision carried).

## Notable decisions and findings

- **Case-insensitive collation** — the silent one. SQL Server `LIKE '%gold%'` matches "Gold In The Dark";
  PostgreSQL does not. Decision (needs owner sign-off): `citext` on the columns the app searches.
  Then a second trap: with `citext` in `public` and the app on `SearchPath=dbo`, PostgreSQL resolved the
  plain case-sensitive `text ~~ text` — **silently**. The extension now lives in `dbo`
  (engine check §17).
- Result-set / cursor procedures → set-returning functions; TRY/CATCH + ambient `ERROR_*()` →
  `EXCEPTION` + parameters to `usplogerror` (signature change recorded in the conversion log).
- `getdate()` CHECKs → static CHECK + trigger; `"order"` reserved word quoted; `money` → `numeric(19,4)`;
  `datetime` tick rounding reproduced (`…59.997`).
- App: EF Core quotes PascalCase → one lower-case fold in `OnModelCreating`; `ToTable("Orders")` was
  pre-existing drift (source table is `Order`); two `int` properties on `bit`→`boolean` columns failed at
  runtime with `42883` → `HasConversion` (now a required fix in `app-scan`).

## Reproducing

```bash
./dbmig inventory      --schema dbo --project bobs
./dbmig convert-schema --schema dbo --project bobs && ./dbmig apply-schema --schema dbo --project bobs
./dbmig convert-code   --schema dbo --project bobs && ./dbmig apply-schema --schema dbo --project bobs --code
./dbmig migrate-data   --schema dbo --project bobs && ./dbmig apply-schema --schema dbo --project bobs --post-data
./dbmig compare        --schema dbo --project bobs
./dbmig gen-tests      --schema dbo --project bobs && ./dbmig run-tests --schema dbo --project bobs
./dbmig app-scan       --app-dir <app-dir>/bobs-used-bookstore-sample --project bobs --target-schema dbo
```

> AI-generated artifacts — review everything before relying on it. See [DISCLAIMER.txt](../DISCLAIMER.txt).
