# High Availability & Disaster Recovery — Oracle → Aurora MySQL

Reference files distilled from the AWS *Oracle Database 19c to Amazon Aurora MySQL Migration Playbook*, HA/DR chapter. Each file maps an Oracle HA/DR or backup/load capability to its Aurora MySQL equivalent, preserving the original code and command examples.

| Reference | Topic | Conversion category |
|---|---|---|
| [active-data-guard-and-replicas.md](active-data-guard-and-replicas.md) | Oracle Active Data Guard → Aurora read replicas / Multi-AZ | N/A (HA infra) |
| [rac-and-aurora-architecture.md](rac-and-aurora-architecture.md) | Oracle RAC → Aurora MySQL cluster architecture | N/A (HA infra) |
| [aurora-mysql-serverless.md](aurora-mysql-serverless.md) | Aurora MySQL Serverless as a RAC alternative | N/A (deployment option) |
| [traffic-director-and-rds-proxy.md](traffic-director-and-rds-proxy.md) | Oracle CMAN Traffic Director → Amazon RDS Proxy | Manual (no automation) |
| [data-pump-and-mysqldump.md](data-pump-and-mysqldump.md) | Oracle Data Pump (expdp/impdp) → mysqldump / mysql / mysqlimport | Manual (non-compatible tool) |
| [flashback-database-and-snapshots.md](flashback-database-and-snapshots.md) | Oracle Flashback Database → snapshots / PITR / Backtrack | Manual (RDS-managed) |
| [flashback-table-and-snapshots.md](flashback-table-and-snapshots.md) | Oracle Flashback Table → snapshots + selective table copy | Manual (RDS-managed) |
| [rman-and-rds-snapshots.md](rman-and-rds-snapshots.md) | Oracle RMAN → Amazon RDS snapshots / automated backups | Manual (RDS-managed) |
| [sqlloader-and-load-data.md](sqlloader-and-load-data.md) | Oracle SQL*Loader → mysqlimport / LOAD DATA / LOAD FROM S3 | Manual (non-compatible tool) |

## Key themes
- **No SCT automation** applies to HA/DR topics — these are architectural and operational substitutions, not schema/code translations.
- **Backup & recovery** (RMAN, Flashback Database/Table) is replaced by RDS-managed snapshots, automated backups, point-in-time restore, and (Aurora MySQL 5.6) Backtrack. Restores generally create a **new cluster/instance** rather than rewinding in place.
- **Clustering & replication** (RAC, ADG) map to Aurora's single-primary + up-to-15-read-replica model over distributed 6-copy/3-AZ storage; Aurora scales out reads, not writes.
- **Connection management** (Traffic Director/CMAN) maps to Amazon RDS Proxy.
- **Bulk load/unload tools** (Data Pump, SQL*Loader) are not cross-compatible; use mysqldump/mysql/mysqlimport, `LOAD DATA`, or Aurora's `LOAD DATA FROM S3`. For cross-engine data movement, use AWS DMS.

> Source playbook chapter root: https://docs.aws.amazon.com/dms/latest/oracle-to-aurora-mysql-migration-playbook/chap-oracle-aurora-mysql.html
