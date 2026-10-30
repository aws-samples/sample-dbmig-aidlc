# Monitoring — Oracle → Aurora MySQL

> Source: AWS Oracle→Aurora MySQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/oracle-to-aurora-mysql-migration-playbook/chap-oracle-aurora-mysql.monitoring.html

Reference material for converting Oracle database monitoring (data dictionary +
V$ dynamic performance views) to Amazon Aurora MySQL.

| Topic | Conversion category | SCT automation | File |
|---|---|---|---|
| Oracle and MySQL monitoring | Manual | N/A | [monitoring.md](monitoring.md) |

## At a glance

- **Oracle**: data dictionary (`DBA_*` / `ALL_*` / `USER_*`) + dynamic
  performance views (`V$*`).
- **MySQL**: `information_schema` tables, `SHOW` commands (`PROCESSLIST`,
  `STATUS`, `GLOBAL VARIABLES`), the `mysql` system schema, `performance_schema`,
  and the `sys` schema.
- **Aurora MySQL**: use **CloudWatch Database Insights** (Performance Insights reached end of life on 2026-07-31) for workload analysis; enable `performance_schema` (off by default).
- All monitoring queries are **manual** rewrites — table/view names differ.

> **Reviewed for Aurora MySQL 8.4 and 3** (validated on 8.4.8 and 3.13.0, 2026-10-29): `INNODB_LOCKS` removed, `performance_schema` off by default, Database Insights replaces Performance Insights.
