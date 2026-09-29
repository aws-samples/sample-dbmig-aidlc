# App intake — Bob's Used Bookstore (.NET, MAM303 branch)
| Item | Value |
|---|---|
| Stack | ASP.NET Core MVC, EF Core 8 (`UseSqlServer`), net8.0, pure LINQ (no SQL text) |
| Git | yes (clean at `0072634`) → backups of edited files only; git is the second safety net |
| Build/run | `dotnet build`; run with `ASPNETCORE_ENVIRONMENT=Development` (local auth, local file service) and `ConnectionStrings__BookstoreDbDefaultConnection` from the environment |
