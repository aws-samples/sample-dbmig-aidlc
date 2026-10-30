# App conversion log — Bob's Used Bookstore

Applied the approved change plan to 4 files (+49 / −13; exact changes in `app.diff`). Backup:
`backup/<ts>/` (the 4 edited files, `MANIFEST.md`); git is the second safety net.

| Change | File | Rule |
|---|---|---|
| `Microsoft.EntityFrameworkCore.SqlServer` → `Npgsql.EntityFrameworkCore.PostgreSQL` 8.0.11 | both `.csproj` | `engines/sqlserver-to-postgresql/app/app-config.yaml` |
| `UseNpgsql`; `NpgsqlConnectionStringBuilder` (Host/Port/Database/`SearchPath=dbo`/`SslMode=Require`); legacy timestamp switch | `ServicesSetup.cs` | app-config.yaml; engine check §17 (citext on the search path) |
| Lower-case fold of names + `HasDefaultSchema("dbo")`; `ToTable("Orders")` → `"Order"` (pre-existing drift, flagged) | `ApplicationDbContext.cs` | `engines/sqlserver-to-postgresql/app/app-sql-rules.md` (EF Core quotes PascalCase) |
| `Address.IsActive`, `ShoppingCartItem.WantToBuy`: `HasConversion(v => v != 0, v => v ? 1 : 0)` | `ApplicationDbContext.cs` | app-scan C1 (int on boolean → 42883) |
