# Monitoring — V$ views / data dictionary → PostgreSQL catalogs & statistics

> Source: AWS Oracle→Aurora PostgreSQL Migration Playbook — Monitoring
> URL: https://docs.aws.amazon.com/dms/latest/oracle-to-aurora-postgresql-migration-playbook/chap-oracle-aurora-pg.monitoring.html

**Conversion category:** Manual (monitoring queries must be rewritten against PostgreSQL catalogs)
**SCT automation:** N/A

> **Reviewed for Aurora PostgreSQL 18** (validated on 18.6, 2026-10-29): PG 16–18 views (`pg_stat_io`, `pg_wait_events`, `pg_stat_checkpointer` split from `pg_stat_bgwriter`), Database Insights replaces Performance Insights.

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
  `pg_publication`, `pg_subscription`. Progress views (≈ `V$SESSION_LONGOPS`):
  `pg_stat_progress_create_index`, `pg_stat_progress_cluster`, `pg_stat_progress_analyze`,
  `pg_stat_progress_vacuum`, `pg_stat_progress_copy` (PG 14+).
- **Cumulative statistics views**: runtime activity — `pg_stat_activity` (sessions / long
  queries / `wait_event_type`+`wait_event` ≈ `V$SESSION.EVENT`), `pg_stat_all_tables`,
  `pg_statio_all_tables`, `pg_stat_database` (cache hit ratio), `pg_stat_all_indexes`
  (unused indexes), `pg_stat_io` (PG 16+, I/O by backend type and context ≈ `V$IOSTAT_*`),
  `pg_stat_wal`, `pg_wait_events` (PG 17+, a catalog of every wait event with a description;
  387 entries on Aurora 18.6), `pg_aios` (PG 18). **Checkpoint statistics moved from
  `pg_stat_bgwriter` to `pg_stat_checkpointer` in PG 17**. On Aurora 18.6,
  `pg_stat_bgwriter` has only `buffers_alloc`, `buffers_clean`, `maxwritten_clean` and
  `stats_reset`, so older monitoring queries that read `checkpoints_timed` fail.
- **Information schema** (SQL-standard, stable across versions): `information_schema.tables`,
  etc. Does not expose PostgreSQL-specific features.
- **CloudWatch Database Insights** (replaces Performance Insights, which reached end of
  life on 2026-07-31): DB load by wait, SQL, host and user, ≈ Oracle ASH/AWR. Standard mode
  is included; Advanced mode adds longer retention, execution plans, and fleet views.
- **Aurora-specific**: the `aurora_stat_utils` extension (`aurora_wait_report()`,
  `aurora_log_report()`) and Aurora wait events prefixed `IO:Aurora…`/`LWLock:Aurora…`.

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
| System statistics | `V$SYSSTAT` | `pg_stat_database`, `pg_stat_io`, `pg_stat_wal`, `pg_stat_checkpointer` |
| Wait events | `V$SESSION_WAIT`, `V$EVENT_NAME` | `pg_stat_activity.wait_event*`, `pg_wait_events` |
| Long operations | `V$SESSION_LONGOPS` | `pg_stat_progress_*` |
| Top SQL | `V$SQLAREA`, AWR | `pg_stat_statements` |
| Table privileges | `DBA_TAB_PRIVS` | `information_schema.table_privileges` |
| I/O operations | `V$SEGSTAT` | `pg_statio_all_tables` |

- Table/object names referenced in monitoring queries must change.
- Enable the `pg_stat_statements` extension for per-query performance analysis (the practical
  replacement for much of Oracle's SQL-level V$ tooling).
- On Aurora, prefer CloudWatch Database Insights + Enhanced Monitoring + CloudWatch over
  hand-rolled catalog queries where possible.
- `pg_stat_statements` 1.12 is preloaded by default on Aurora 18, so run
  `CREATE EXTENSION pg_stat_statements;` in each database you want to query it from.
