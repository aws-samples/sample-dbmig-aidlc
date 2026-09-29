# Build & validation report — .NET app on Aurora PostgreSQL

1. `dotnet build` → succeeded (net8.0; run with `DOTNET_ROLL_FORWARD=Major` on a .NET 10 host).
2. Boot (Development profile, connection from env) → `Now listening`; EF queries against `dbo`.
3. Found only at runtime (not by compile): `42883 boolean = integer` on `/Address` → fix #5 (app-scan
   now reports int-on-boolean as a required fix); search for `gold` returned nothing → citext decision,
   then `citext` in `public` not on `SearchPath=dbo` → extension moved to `dbo`.
4. Endpoints: `/` · `/Search?SearchString=gold|GOLD|children of` (hits) · `/Search/Details/1` ·
   `/ShoppingCart` · `/Wishlist` · `/Address` · `/Admin/Dashboard|Inventory|Offers|Orders|ReferenceData` → 200; 0 PostgreSQL errors.

UNVERIFIED: write paths (checkout, offers) — read-only validation.
