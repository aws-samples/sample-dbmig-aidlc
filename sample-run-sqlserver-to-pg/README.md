# Sample run — SQL Server `BobsUsedBookStore` → Aurora PostgreSQL (+ .NET EF Core app)

A complete, real run **converted from scratch** by dbmig-aidlc (for the path that *continues from AWS DMS
Schema Conversion*, see [`sample-run-dms-sc-sqlserver-to-pg/`](../sample-run-dms-sc-sqlserver-to-pg/)).
Masked: hosts, account ids, local paths and credentials are placeholders.

- **Source:** SQL Server 2022 (RDS), `BobsUsedBookStore.dbo` (collation `SQL_Latin1_General_CP1_CI_AS`)
- **Target:** Aurora PostgreSQL 17.7, schema `dbo`
- **App:** Bob's Used Bookstore .NET (branch `MAM303`), ASP.NET Core + EF Core 8, pure LINQ

## Result at a glance

| Phase | Result |
|---|---|
| Inventory | 20 tables, 4 views, 7 functions, 14 procedures, 2,963 rows; decision item **`case_insensitive_collation`** (82 `_CI_` string columns) |
| Tables / code | **20/20** and **25/25** applied first pass; post-data **6/6** |
| Data | **20/20** tables reconcile; identity **14/14** safe |
| Equivalence tests | **68/68** — first run 56/68 exposed 3 real defects (smallint parameter lookup, `'0000000*'` overflow marker, INOUT call shape); fixed; 12 follow-ups auto-resolved |
| App | 4 files (+49/−13); builds; boots against the migrated schema; search, details, cart, address, admin pages 200 with 0 PostgreSQL errors |
| Prompt volume | ≈ 30K tokens (4 + 4 + 5 bundles + 3 shared context files) |

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
