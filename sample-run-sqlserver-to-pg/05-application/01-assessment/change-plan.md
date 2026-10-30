# Change plan — Bob's Used Bookstore → Aurora PostgreSQL 18.6 (like-for-like)

From `dbmig app-scan` (141 files, EF Core detected, 9 entities / 90 mapped fields checked against the live
`bookstore.dbo` schema on 18.6: **82 identifier-case issues, 8 fields on the drifted `Orders` table, 2 required type fixes** —
the same findings as the previous run on 17.7, so the previous, validated change set is re-applied). Nothing was edited
before this plan; backup: edited files only (git repo).

| # | Site | Class | Change |
|---|---|---|---|
| 1 | `Bookstore.Data.csproj`, `Bookstore.Web.csproj` | mechanical | `Microsoft.EntityFrameworkCore.SqlServer` → `Npgsql.EntityFrameworkCore.PostgreSQL` 8.0.11 |
| 2 | `ServicesSetup.cs` `UseSqlServer` + `SqlConnectionStringBuilder` (built in code) | mechanical | `UseNpgsql`; `NpgsqlConnectionStringBuilder` (Host/Port/Database/SearchPath=dbo/SslMode=Require); MARS/TrustServerCertificate dropped; `Npgsql.EnableLegacyTimestampBehavior` (DateTime.UtcNow into `timestamp` columns, like SQL Server) |
| 3 | EF model quotes PascalCase (`"Book"`, `"AddressLine1"`) vs folded target | required | lower-case fold of tables/columns/keys/indexes in `OnModelCreating` + `HasDefaultSchema("dbo")` |
| 4 | `ToTable("Orders")` — source table is `Order` | **pre-existing drift** | conform to the migrated `order` table; flagged |
| 5 | `Address.IsActive`, `ShoppingCartItem.WantToBuy` are `int` on `bit` → `boolean` | required | `.HasConversion(v => v != 0, v => v ? 1 : 0)` (LINQ `== 1` failed with 42883) |
| 6 | case-insensitive search (`.Contains`) | BEHAVIOURAL | resolved DB-side by the citext decision — no app change |
| — | EF migrations / `EnsureCreated` on startup | note | `EnsureCreated` only runs if the DB is unreachable; do not use SQL Server migration history |
| — | `/Authentication/Login` without `redirectUri` → NullReferenceException | pre-existing | not migration-related |
