# Configuration — Oracle→Aurora MySQL Playbook References

Distilled reference pages from the **AWS Oracle Database 19c to Amazon Aurora MySQL Migration Playbook**, "Configuration" chapter. These cover instance/session configuration, memory, logging, and upgrade differences between Oracle and Aurora MySQL.

> **Reviewed for Aurora MySQL 8.4 and 3** (validated on 8.4.8 and 3.13.0, 2026-10-29). Baseline: `../target-baseline-aurora-mysql.md`.

| File | Topic | Key difference |
|---|---|---|
| [upgrades.md](upgrades.md) | Oracle and Aurora MySQL upgrades | Managed in-place upgrades; version schemes 3.x (MySQL 8.0) and 8.4.x; 3 → 8.4 breaking changes; blue/green deployments |
| [alert-log-and-error-log.md](alert-log-and-error-log.md) | Oracle alert log vs MySQL error log | `alert.log` → error log exported to CloudWatch Logs + RDS events → SNS; ORA- → MySQL error-code table |
| [memory-sizing-and-buffers.md](memory-sizing-and-buffers.md) | SGA/PGA sizing vs MySQL memory buffers | RAM bound to instance class or Serverless v2 ACUs; `innodb_buffer_pool_size`; no PGA-style aggregate limit |
| [instance-parameters-and-parameter-groups.md](instance-parameters-and-parameter-groups.md) | Instance parameters vs parameter groups | `ALTER SYSTEM`/SPFILE → `aurora-mysql8.4`/`8.0` parameter groups; parameters migrations usually change (`sql_mode`, isolation, time zone) |
| [session-parameters-and-variables.md](session-parameters-and-variables.md) | Session parameters vs session variables | `ALTER SESSION` → `SET SESSION`; `USE` for `current_schema`; `optimizer_trace` for 10053; no `SET GLOBAL` for the master user |

> All five pages carry SCT/DMS automation level **N/A** — these are configuration and operational differences, not automated schema conversions.
