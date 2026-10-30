# App scan — `bobs` (sqlserver-to-postgresql)

Deterministic pre-scan by `dbmig app-scan` (read-only). **Open only the flagged files**; full detail in `app-scan.yaml`.

- files in scope: **141** (.cs 129, .csproj 5, .js 4, .json 3)
- frameworks detected: EF Core (14 file(s))
- excluded dirs: .git×1, vendored-asset×145
- leftovers (not conversion targets): none
- **flagged files: 14 of 141**

| Category | Sites | Files |
|---|---|---|
| A. config (datasource/driver/dialect; plaintext secrets) | 7 | 3 |
| A. connection strings/URLs built in code | 3 | 1 |
| B. embedded SQL with source-dialect constructs | 0 | 0 |
| B. other embedded SQL (no construct hit — still review for case/quoting) | 0 | 0 |
| C1. mapped fields with a REQUIRED type fix | 2 | 2 |
| C1. type advisories (not blockers; review) | 0 | 0 |
| C1. mapping issues (missing table/column, identifier case) | 90 | 10 |
| D. stored-routine call sites | 0 | 0 |
| E. error-code handling | 0 | 0 |
| F. result-set typing / column-name access | 0 | 0 |
| H. source-engine SQL scripts shipped with the app (flag; not converted unless in scope) | 0 | 0 |

Entities/models: 9 (EF Core 9); 90 mapped field(s) checked against **live target catalog (schema dbo)**.

## C1. Required type fixes (entity field ↔ migrated column)

- `app/Bookstore.Domain/Addresses/Address.cs:39` EF Core Address.IsActive (int) → Address.IsActive [boolean]: integer field on boolean column (the source bit/NUMBER(1) accepted `= 1`; PostgreSQL raises 42883 boolean = integer): .HasConversion(v => v != 0, v => v ? 1 : 0) in OnModelCreating (keeps the int model; LINQ `x.Flag == 1` then translates to a boolean comparison)
- `app/Bookstore.Domain/Carts/ShoppingCartItem.cs:27` EF Core ShoppingCartItem.WantToBuy (int) → ShoppingCartItem.WantToBuy [boolean]: integer field on boolean column (the source bit/NUMBER(1) accepted `= 1`; PostgreSQL raises 42883 boolean = integer): .HasConversion(v => v != 0, v => v ? 1 : 0) in OnModelCreating (keeps the int model; LINQ `x.Flag == 1` then translates to a boolean comparison)

## C1. Mapping issues

- EF Core Address → Address: identifier case — 12 field(s), e.g. `app/Bookstore.Domain/Addresses/Address.cs:24` AddressLine1: identifier case: the ORM quotes "AddressLine1" but the target folded it to addressline1 — fold names in the model
- EF Core Book → Book: identifier case — 16 field(s), e.g. `app/Bookstore.Domain/Books/Book.cs:37` Name: identifier case: the ORM quotes "Name" but the target folded it to name — fold names in the model
- EF Core Customer → Customer: identifier case — 11 field(s), e.g. `app/Bookstore.Domain/Customers/Customer.cs:13` Sub: identifier case: the ORM quotes "Sub" but the target folded it to sub — fold names in the model
- EF Core Offer → Offer: identifier case — 17 field(s), e.g. `app/Bookstore.Domain/Offers/Offer.cs:31` Author: identifier case: the ORM quotes "Author" but the target folded it to author — fold names in the model
- EF Core Order → Orders: table `Orders` not in target schema `dbo` — 8 field(s), e.g. `app/Bookstore.Domain/Orders/Order.cs:19` CustomerId: table `Orders` not in target schema `dbo`
- EF Core OrderItem → OrderItem: identifier case — 7 field(s), e.g. `app/Bookstore.Domain/Orders/OrderItem.cs:19` OrderId: identifier case: the ORM quotes "OrderId" but the target folded it to orderid — fold names in the model
- EF Core ReferenceDataItem → ReferenceData: identifier case — 6 field(s), e.g. `app/Bookstore.Domain/ReferenceData/ReferenceDataItem.cs:17` DataType: identifier case: table "ReferenceData" is quoted by the ORM; target has referencedata — fold names in the model
- EF Core ShoppingCart → ShoppingCart: identifier case — 5 field(s), e.g. `app/Bookstore.Domain/Carts/ShoppingCart.cs:7` CorrelationId: identifier case: the ORM quotes "CorrelationId" but the target folded it to correlationid — fold names in the model
- EF Core ShoppingCartItem → ShoppingCartItem: identifier case — 8 field(s), e.g. `app/Bookstore.Domain/Carts/ShoppingCartItem.cs:19` ShoppingCartId: identifier case: the ORM quotes "ShoppingCartId" but the target folded it to shoppingcartid — fold names in the model

## A. Connection strings/URLs built in code

- `app/Bookstore.Web/Startup/ServicesSetup.cs:34` — `builder.Services.AddDbContext<ApplicationDbContext>(option => option.UseSqlServer(connString));`
- `app/Bookstore.Web/Startup/ServicesSetup.cs:91` — `var partialConnString = $"Server={dbSecrets.Host},{dbSecrets.Port}; Initial Catalog=BobsUsedBookStore;MultipleActiveResultSets=true; Integra`
- `app/Bookstore.Web/Startup/ServicesSetup.cs:93` — `var builder = new SqlConnectionStringBuilder(partialConnString)`

## A. Configuration

- `app/Bookstore.Data/Bookstore.Data.csproj:16` — `<PackageReference Include="Microsoft.EntityFrameworkCore.Design" Version="8.0.11" />`
- `app/Bookstore.Data/Bookstore.Data.csproj:17` — `<PackageReference Include="Microsoft.EntityFrameworkCore.SqlServer" Version="8.0.11" />`
- `app/Bookstore.Data/Bookstore.Data.csproj:18` — `<PackageReference Include="Microsoft.EntityFrameworkCore.Tools" Version="8.0.11" />`
- `app/Bookstore.Web/Bookstore.Web.csproj:20` — `<PackageReference Include="Microsoft.EntityFrameworkCore.Sqlite" Version="8.0.11" />`
- `app/Bookstore.Web/Bookstore.Web.csproj:21` — `<PackageReference Include="Microsoft.EntityFrameworkCore.SqlServer" Version="8.0.11" />`
- `app/Bookstore.Web/Bookstore.Web.csproj:22` — `<PackageReference Include="Microsoft.EntityFrameworkCore.Tools" Version="8.0.20" />`
- `app/Bookstore.Web/appsettings.Test.json:2` — `"ConnectionStrings": {`

## Flagged files (open these; the rest had no hits)

- `app/Bookstore.Data/Bookstore.Data.csproj`
- `app/Bookstore.Domain/Addresses/Address.cs`
- `app/Bookstore.Domain/Books/Book.cs`
- `app/Bookstore.Domain/Carts/ShoppingCart.cs`
- `app/Bookstore.Domain/Carts/ShoppingCartItem.cs`
- `app/Bookstore.Domain/Customers/Customer.cs`
- `app/Bookstore.Domain/Entity.cs`
- `app/Bookstore.Domain/Offers/Offer.cs`
- `app/Bookstore.Domain/Orders/Order.cs`
- `app/Bookstore.Domain/Orders/OrderItem.cs`
- `app/Bookstore.Domain/ReferenceData/ReferenceDataItem.cs`
- `app/Bookstore.Web/Bookstore.Web.csproj`
- `app/Bookstore.Web/Startup/ServicesSetup.cs`
- `app/Bookstore.Web/appsettings.Test.json`

Limits: static scanning cannot see SQL assembled from configuration/the database or generated by ORM criteria/LINQ; an ORM app with zero SQL text can still break (identifier case, types). The boot against the migrated target (Validation) is the proof.
