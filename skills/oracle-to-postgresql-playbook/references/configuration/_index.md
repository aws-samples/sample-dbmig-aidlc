# Configuration References — Oracle → Aurora PostgreSQL

Distilled from the AWS *Oracle to Aurora PostgreSQL Migration Playbook* (Configuration chapter). Reference only — test everything in a non-production environment first.

- [upgrades.md](upgrades.md) — Oracle minor/major version upgrade process vs. managed Aurora PostgreSQL upgrades (parameter groups, `reg*` type and prepared-transaction prerequisites, console/CLI steps).
- [alert-log-and-error-log.md](alert-log-and-error-log.md) — Oracle Alert Log (`alert<sid>.log`, ADR) vs. PostgreSQL error log (severity levels, RDS console access, `log_*` config params, SNS event notifications).
- [memory-sizing-and-buffers.md](memory-sizing-and-buffers.md) — Oracle SGA/PGA pools vs. PostgreSQL memory buffers (`shared_buffers`, `wal_buffers`, `work_mem`, etc.) and Aurora instance-class sizing.
- [instance-parameters-and-rds-parameter-groups.md](instance-parameters-and-rds-parameter-groups.md) — Oracle `ALTER SYSTEM`/SPFILE vs. Aurora cluster and database parameter groups, including AWS-optimized default formulas.
- [session-parameters.md](session-parameters.md) — Oracle `ALTER SESSION` vs. PostgreSQL `SET SESSION`/`SET LOCAL`, with a side-by-side parameter mapping.
