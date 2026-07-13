# Configuration — Oracle→Aurora MySQL Playbook References

Distilled reference pages from the **AWS Oracle Database 19c to Amazon Aurora MySQL Migration Playbook**, "Configuration" chapter. These cover instance/session configuration, memory, logging, and upgrade differences between Oracle and Aurora MySQL.

| File | Topic | Key difference |
|---|---|---|
| [upgrades.md](upgrades.md) | Oracle and Aurora MySQL upgrades | Oracle install-and-upgrade vs Aurora managed in-place upgrades (console/CLI) |
| [alert-log-and-error-log.md](alert-log-and-error-log.md) | Oracle alert log vs MySQL error log | File-based `alert<sid>.log` → RDS console logs + SNS event notifications |
| [memory-sizing-and-buffers.md](memory-sizing-and-buffers.md) | SGA/PGA sizing vs MySQL memory buffers | Different cache names, similar usage; RAM bound to instance class |
| [instance-parameters-and-parameter-groups.md](instance-parameters-and-parameter-groups.md) | Instance parameters vs parameter groups | `ALTER SYSTEM`/SPFILE → cluster & DB parameter groups |
| [session-parameters-and-variables.md](session-parameters-and-variables.md) | Session parameters vs session variables | `ALTER SESSION` → `SET SESSION`; `SET` options significantly different |

> All five pages carry SCT/DMS automation level **N/A** — these are configuration and operational differences, not automated schema conversions.
