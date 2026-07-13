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
- **Aurora MySQL**: use **Performance Insights** for workload analysis.
- All monitoring queries are **manual** rewrites — table/view names differ.
