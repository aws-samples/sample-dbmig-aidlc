# Configuration — SQL Server → Aurora PostgreSQL

Reference files distilled from the AWS SQL Server→Aurora PostgreSQL Migration Playbook, "Configuration" chapter. Each page compares SQL Server behavior with Aurora PostgreSQL and notes how settings map to Aurora Parameter Groups.

| File | Topic | Conversion category | Key difference |
|---|---|---|---|
| [upgrades.md](upgrades.md) | Configuring Upgrades | N/A | In-place/new-install (SQL Server) vs. managed RDS console/CLI upgrades; no auto major upgrades |
| [session-options.md](session-options.md) | Configuring Session Options | N/A (★★) | `SET` options differ significantly except transaction isolation; `SET ROWCOUNT` for DML → `TOP`/`LIMIT` |
| [database-options.md](database-options.md) | Configuring Database Options | N/A (★) | `ALTER DATABASE … SET` → AWS Database Parameter Group |
| [server-options.md](server-options.md) | Configuring Server Options | N/A (★) | `sp_configure`/`RECONFIGURE` → AWS Cluster & Database Parameter Groups |

## Quick orientation

- **Server options** → Aurora **Cluster Parameter Group** (cluster-wide: `wal_buffers`, `autovacuum`, `client_encoding`) plus **Database Parameter Group** (per-instance: `shared_buffers`, `max_connections`, `effective_cache_size`).
- **Database options** → Aurora **Database Parameter Group**.
- **Session options** → PostgreSQL `SET SESSION` parameters (`client_encoding`, `lock_timeout`, `search_path`, `transaction_isolation`, etc.); inspect via `SELECT * FROM pg_settings WHERE context = 'user';`.
- **Upgrades** → managed via RDS console or `aws rds modify-db-cluster`; major upgrades need `--allow-major-version-upgrade`, a version-compatible parameter group, removal of `reg*` types, extension upgrades, and committed prepared transactions.
