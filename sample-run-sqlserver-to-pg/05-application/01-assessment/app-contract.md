# App contract — what the DB migration changed → what the app must change

| DB change (source) | Required app change |
|---|---|
| SQL Server → Aurora PostgreSQL 18.6, schema `dbo` (`00-intake/intake.md`) | EF Core provider `UseSqlServer` → `UseNpgsql`; Npgsql connection (`SearchPath=dbo`, `SslMode=Require`) — `engines/sqlserver-to-postgresql/app/app-config.yaml` |
| Identifiers folded to lower case (`02-construction/conversion-log.md`; carry-forward 4) | fold EF table/column/key/index names in `OnModelCreating` |
| `bit` → `boolean` (carry-forward 2) | `int` properties on `bit` columns: `HasConversion<bool>` |
| `citext` in schema `dbo` (carry-forward 3) | connect with `SearchPath=dbo` so LIKE stays case-insensitive |
| `datetime2` → `timestamp` without time zone | `Npgsql.EnableLegacyTimestampBehavior` (UTC `DateTime` values stored as given, like SQL Server) |
| Result-set procedures became functions (carry-forward 1) | no app call sites (pure LINQ) |
| Source table is `Order`; model maps `Orders` | conform to `order`; flag as pre-existing drift |
