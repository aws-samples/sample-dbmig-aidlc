---
name: oracle-to-mysql-playbook
description: Knowledge base for converting Oracle to MySQL (Aurora MySQL compatible), distilled from the AWS Oracle-to-Aurora-MySQL Migration Playbook into granular per-topic references. Use when converting or assessing a specific Oracle construct for a MySQL target — datatypes, SQL/PL-SQL (MERGE, sequences/AUTO_INCREMENT, cursors, packages, dynamic SQL, DBMS_* packages, regex, timezone), tables/partitioning, triggers, views, materialized views, JSON/XML, synonyms, database links, security/privileges, HA/DR, configuration, performance tuning, or monitoring — and you need the MySQL equivalent, the conversion difficulty, and the workaround. The db-migration-inception and db-migration-construction skills consult this when the target engine is MySQL. This is a reference index/router: load the specific topic file under references/ rather than reading everything.
---

# Oracle → MySQL Playbook (reference index)

Granular conversion references distilled from the AWS *Oracle Database 19c to Amazon Aurora
MySQL Migration Playbook*. **Reference only — test everything in a non-production environment
first.**

## How to use this skill

A **router**, not a document to read end-to-end. Given an Oracle construct:
1. Find the topic below and open that single file under `references/`.
2. Each file states a **Conversion category** (Automatic / Assisted / Manual / Blocked),
   shows the Oracle and MySQL forms, and lists conversion notes/gotchas.
3. Cite the file path in the conversion log / assessment for traceability.

Each chapter folder also has an `_index.md` with one-line summaries.

### MySQL specifics to keep in mind
- A MySQL **schema is a database**; the Oracle schema maps to a MySQL database.
- Identifiers are quoted with **backticks**; default storage engine is **InnoDB**.
- **No packages** (split into individual stored routines), **no MERGE** (use
  `INSERT ... ON DUPLICATE KEY UPDATE`), **no sequences pre-8.0** (use `AUTO_INCREMENT`).
- Empty string `''` is **not** NULL (differs from Oracle).

### Conversion categories
- **Automatic** — direct equivalent, low risk.
- **Assisted** — mechanical rewrite with a known pattern.
- **Manual** — needs redesign / human judgment.
- **Blocked** — no supported path; flag to the user and find an architectural alternative.

## Precedence: customer-specific knowledge wins

`references/customer-specific/` holds this customer's environment/application rules and has
**higher precedence than every general reference**. The conversion tooling injects active
files from that folder at the top of each prompt bundle. Consult `customer-specific/` first,
then fall back to the general references. See `customer-specific/_index.md`.

## Topic map

### customer-specific/ — HIGHEST PRECEDENCE (this customer's environment/application)
- Populated per engagement; overrides everything below on conflict.

### tools/ — migration tooling
- `native-tools.md` (informational; dbmig uses Python drivers), `aws-sct.md`,
  `sct-action-code-index.md`, `aws-dms.md`, `rds-on-outposts.md`, `rds-proxy.md`,
  `aurora-serverless-v1.md`, `aurora-parallel-query.md`, `aurora-backtrack.md`

### sql-plsql/ — SQL & PL/SQL (the bulk of code conversion)
- Functions/queries: `single-row-and-aggregate-functions.md`, `conversion-functions.md`,
  `create-table-as-select.md`, `common-table-expressions.md`, `insert-from-select.md`,
  `merge-statement.md`, `olap-and-window-functions.md`, `regular-expressions.md`,
  `multi-version-concurrency-control.md`
- Identity/sequences/txns: `sequences-and-auto-increment.md`, `transaction-model.md`,
  `timezone-and-convert-tz.md`
- PL/SQL: `anonymous-block.md`, `cursors.md`, `procedures-and-functions.md`,
  `user-defined-functions.md`, `execute-immediate-and-prepare.md`, `dbms-sql.md`
- DBMS_*/UTL_*: `dbms-output-and-select.md`, `dbms-random-and-rand.md`,
  `dbms-redefinition.md`, `dbms-datapump-and-s3.md`, `utl-file-and-s3.md`,
  `utl-mail-smtp-and-sns.md`

### special-features/ — Oracle-specific features
- `advanced-queuing-and-lambda.md`, `character-sets.md`, `database-links-and-fqtn.md`,
  `dbms-scheduler-and-events.md`, `external-tables-and-s3.md`, `inline-views.md`,
  `json-support.md`, `materialized-views-and-summary-tables.md`,
  `multitenant-and-databases.md`, `resource-manager-and-dedicated-clusters.md`,
  `securefile-lobs-and-large-objects.md`, `synonyms.md`, `views.md`, `xml-db-and-xml.md`,
  `table-compression.md`, `log-miner-and-logs.md`, `sql-result-cache-and-query-cache.md`

### ha-dr/ — high availability & disaster recovery
- `active-data-guard-and-replicas.md`, `rac-and-aurora-architecture.md`,
  `aurora-mysql-serverless.md`, `traffic-director-and-rds-proxy.md`,
  `data-pump-and-mysqldump.md`, `flashback-database-and-snapshots.md`,
  `flashback-table-and-snapshots.md`, `rman-and-rds-snapshots.md`,
  `sqlloader-and-load-data.md`

### configuration/
- `upgrades.md`, `alert-log-and-error-log.md`, `memory-sizing-and-buffers.md`,
  `instance-parameters-and-parameter-groups.md`, `session-parameters-and-variables.md`

### performance-tuning/
- `database-hints.md`, `run-plans.md`, `table-statistics.md`

### security/
- `encrypted-connections.md`, `tde-and-encryption.md`, `roles-and-privileges.md`, `users.md`

### physical-storage/
- `table-partitioning.md`, `sharding.md`

### monitoring/
- `monitoring.md` (V$/data-dictionary → information_schema / performance_schema / sys; Performance Insights)

### quick-tips/
- `quick-tips.md` — fast checklist of common gotchas; start here, then drill into the topic file.

## Cross-references
- Datatype mapping: `engines/oracle-to-mysql/datatype-map.yaml`
- Equivalence-testing methodology: `engines/oracle-to-mysql/checks/equivalence-spec.md`
- Application-layer conversion rules (embedded SQL, drivers/ORM, error codes) for this pair: `engines/oracle-to-mysql/app/` — used by the optional `app-modernization-orchestrator` module, not by DB-schema conversion.
