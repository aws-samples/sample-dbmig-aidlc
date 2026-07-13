# Monitoring — V$ views / data dictionary → PostgreSQL catalogs & statistics

> Source: AWS Oracle→Aurora PostgreSQL Migration Playbook — Monitoring
> URL: https://docs.aws.amazon.com/dms/latest/oracle-to-aurora-postgresql-migration-playbook/chap-oracle-aurora-pg.monitoring.html

**Conversion category:** Manual (monitoring queries must be rewritten against PostgreSQL catalogs)
**SCT automation:** N/A

## Oracle
Oracle exposes operational state through:
- **Data dictionary** (persistent metadata): `DBA_*`, `ALL_*`, `USER_*` views — e.g.
  `DBA_TABLES`, `DBA_USERS`, `DBA_DATA_FILES`, `DBA_TABLESPACES`, `DBA_TAB_COLS`.
- **Dynamic performance views** (`V$`): real-time instance state — e.g. `V$SESSION`,
  `V$LOCKED_OBJECT`, `V$INSTANCE`, `V$SESSION_LONGOPS`, `V$PARAMETER`, `V$SYSSTAT`.

## PostgreSQL
Three metadata sources plus a managed console:
- **System catalog tables** (`pg_*` in `pg_catalog`): static metadata — `pg_database`,
  `pg_tables`, `pg_index`, `pg_cursors`, `pg_sequences`, `pg_partitioned_table`,
  `pg_publication`, `pg_subscription`. Progress views: `pg_stat_progress_create_index`,
  `pg_stat_progress_cluster`, `pg_stat_progress_analyze` (PG12/13+).
- **Statistics collector views**: runtime activity — `pg_stat_activity` (sessions / long
  queries), `pg_stat_all_tables`, `pg_statio_all_tables`, `pg_stat_database` (cache hit
  ratio), `pg_stat_bgwriter` (checkpoints), `pg_stat_all_indexes` (unused indexes).
- **Information schema** (SQL-standard, stable across versions): `information_schema.tables`,
  etc. Does not expose PostgreSQL-specific features.
- **Amazon RDS / Aurora Performance Insights**: visual load monitoring (waits, SQL, hosts,
  users); enabled by default on Aurora, 24h retention. Console → RDS → Performance Insights.

## Conversion notes
Quick equivalence map for rewriting monitoring queries:

| Information | Oracle | PostgreSQL |
|---|---|---|
| Database properties | `V$DATABASE` | `pg_database` |
| Sessions | `V$SESSION` | `pg_stat_activity` |
| Users | `DBA_USERS` | `pg_user` |
| Tables | `DBA_TABLES` | `pg_tables` |
| Roles | `DBA_ROLES` | `pg_roles` |
| Table columns | `DBA_TAB_COLS` | `pg_attribute` |
| Locks | `V$LOCKED_OBJECT` | `pg_locks` |
| Runtime parameters | `V$PARAMETER` | `pg_settings` |
| System statistics | `V$SYSSTAT` | `pg_stat_database` |
| Table privileges | `DBA_TAB_PRIVS` | `information_schema.table_privileges` |
| I/O operations | `V$SEGSTAT` | `pg_statio_all_tables` |

- Table/object names referenced in monitoring queries must change.
- Enable the `pg_stat_statements` extension for per-query performance analysis (the practical
  replacement for much of Oracle's SQL-level V$ tooling).
- On Aurora, prefer Performance Insights + Enhanced Monitoring + CloudWatch over hand-rolled
  catalog queries where possible.
