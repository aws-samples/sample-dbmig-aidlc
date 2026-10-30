# Build & validation report — Bob's Used Bookstore → Aurora PostgreSQL 18.6

| Check | Result |
|---|---|
| `dotnet build` (net8.0 on a .NET 10 SDK host, `DOTNET_ROLL_FORWARD=Major`) | **pass**, 0 errors |
| Run (Development profile, connection from the environment, bound to 127.0.0.1) | **pass** — `Now listening`; 0 PostgreSQL errors in the log |

## Verification matrix

| Path | Result |
|---|---|
| `/` | 200 |
| `/Search?SearchString=gold` / `GOLD` / `children of` | 200, each returns the expected book (case-insensitive via `citext` on `SearchPath=dbo`) |
| `/Search/Details/1` | 200 |
| `/ShoppingCart`, `/Wishlist` | 200 |
| `/Address` (the `int` ↔ `boolean` conversion) | 200 |
| `/Admin/Dashboard`, `/Admin/Inventory`, `/Admin/Offers`, `/Admin/Orders`, `/Admin/ReferenceData` | 200 |

All required fixes were known before the first run (app-scan C1 + the previous run's findings); no runtime-only
fix was needed this time. The app redirects HTTP to HTTPS, so the smoke run used the HTTPS listener.

**UNVERIFIED:** write paths (checkout, offers) — read-only smoke.
**Pre-existing (unchanged):** `/Authentication/Login` without `redirectUri` throws a NullReferenceException.
