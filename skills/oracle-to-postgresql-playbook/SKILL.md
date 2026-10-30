---
name: oracle-to-postgresql-playbook
description: Knowledge base for converting Oracle to PostgreSQL (Aurora PostgreSQL compatible), distilled from the AWS Oracle-to-Aurora-PostgreSQL Migration Playbook into granular per-topic references and refreshed for an Aurora PostgreSQL 18 target (validated on 18.6). Use when converting or assessing a specific Oracle construct — datatypes, SQL/PL-SQL (MERGE, sequences, cursors, packages, dynamic SQL, DBMS_* packages), tables/indexes, partitioning, triggers, views, materialized views, JSON/XML, database links, security/roles, HA/DR, configuration, performance tuning, or monitoring — and you need the PostgreSQL equivalent, the conversion difficulty, and the workaround. The db-migration-inception and db-migration-construction skills consult this to classify and convert objects. This is a reference index/router: load the specific topic file under references/ rather than reading everything.
---

# Oracle → PostgreSQL Playbook (reference index)

Granular conversion references distilled from the AWS *Oracle Database 19c to Amazon Aurora
PostgreSQL Migration Playbook*. **Reference only — test everything in a non-production
environment first.**

## Target version baseline: Aurora PostgreSQL 18

The AWS playbook was written for Aurora PostgreSQL 10–13. Every file here has been reviewed
and refreshed for **Aurora PostgreSQL 18** and validated on a live 18.6 cluster on 2026-10-29.
Each topic file carries a `Reviewed for Aurora PostgreSQL 18` line naming what changed, and
statements marked *verified* were executed on that cluster.

- New migrations should target the latest major version (18). Older advice that was only a
  workaround for missing features (procedures as `RETURNS VOID` functions, `MERGE` via
  `ON CONFLICT`, trigger-based virtual columns, regex emulation, `SERIAL`, uuid-ossp) is
  superseded. The topic files say so explicitly.
- If a customer must target an older major version, the version annotations in each file
  (for example "PG 15+", "PG 17+") show which defaults still apply. Record the decision in
  `customer-specific/environment.md`.
- **Start with `references/target-baseline-aurora-postgresql-18.md`**: PG 18 conversion
  defaults, what still has no equivalent, verified behavior differences, and the Aurora 18.6
  extension and parameter inventory.

## How to use this skill

A **router**, not a document to read end-to-end. Given an Oracle construct:
1. Find the topic below and open that single file under `references/`.
2. Each file states a **Conversion category** (Automatic / Assisted / Manual / Blocked),
   shows the Oracle and PostgreSQL forms, and lists conversion notes/gotchas.
3. Cite the file path in the conversion log / assessment for traceability.

Each chapter folder also has an `_index.md` with one-line summaries.

### Conversion categories
- **Automatic** — direct equivalent, low risk.
- **Assisted** — mechanical rewrite with a known pattern.
- **Manual** — needs redesign / human judgment.
- **Blocked** — no supported path; flag to the user and find an architectural alternative.

## How this playbook is consumed

Only the parts below are read by a phase; keep them current first.

| Consumer | What it reads |
|---|---|
| Construction and Validation (automatic) | `dbmig` writes the shared `_context-<phase>.md` with: the selected sections of `references/target-baseline-aurora-postgresql-18.md` (configured by `conversion.target_baseline` in `engines/oracle-to-postgresql/engine.yaml`), `quick-tips/quick-tips.md` in full, and the `_index.md` of `tables-indexes/`, `physical-storage/`, `special-features/` (schema); `sql-plsql/`, `special-features/` (code). The test context gets the baseline's behavior-differences section. |
| Construction (on demand) | The topic file named in each detected-construct hint (`— see skills/oracle-to-postgresql-playbook/references/…`); the converter cites it in `conversion-log.md`, and `./dbmig status` counts the citations. |
| DMS SC ingest | `tools/sct-action-code-index.md` to judge DMS SC action items. |
| Operations | `tools/aws-dms.md`, `tools/rds-proxy.md`, `ha-dr/`, `configuration/`, `monitoring/`, `performance-tuning/`. |
| Reference only | the other `tools/` files (`native-tools.md`, `rds-on-outposts.md`, `aurora-serverless-v1.md`, `aws-sct.md`) and `security/`. No phase reads these; refresh them only when someone needs them. |

## Precedence: customer-specific knowledge wins

`references/customer-specific/` holds this customer's environment/application rules and has
**higher precedence than every general reference**. The conversion tooling injects active
files from that folder at the top of each prompt bundle. Consult `customer-specific/` first,
then fall back to the general references. See `customer-specific/_index.md`.

## Topic map

### customer-specific/ — HIGHEST PRECEDENCE (this customer's environment/application)
- Populated per engagement. Overrides everything below on conflict. See `_index.md`.

### target-baseline-aurora-postgresql-18.md — read first
- PG 18 conversion defaults, remaining gaps, verified behavior differences, Aurora 18.6 inventory.

### tools/ — migration tooling
- `native-tools.md` (sqlplus/SQLcl/psql — informational; dbmig uses Python drivers),
  `aws-sct.md`, `sct-action-code-index.md` (incl. codes obsolete on PG 18), `aws-dms.md`
  (PG 18 targets need DMS 3.5.4+), `rds-on-outposts.md`, `rds-proxy.md`,
  `aurora-serverless-v1.md` (now Serverless v2; v1 is end-of-life)

### sql-plsql/ — SQL & PL/SQL (the bulk of code conversion)
- Functions/queries: `single-row-and-aggregate-functions.md`, `create-table-as-select.md`,
  `common-table-expressions.md`, `insert-from-select.md`, `merge-statement.md`,
  `olap-and-window-functions.md`, `multi-version-concurrency-control.md`
- Identity/sequences/txns: `identity-columns-and-serial.md`, `sequences.md`,
  `transaction-model.md`
- PL/SQL: `anonymous-block-and-do.md`, `cursors.md`, `procedures-and-functions.md`,
  `user-defined-functions.md`, `execute-immediate-and-prepare.md`,
  `dbms-sql-dynamic-execution.md`
- DBMS_* packages: `dbms-output-and-raise.md`, `dbms-random-and-random.md`, `utl-file.md`,
  `utl-mail-smtp-and-ses.md`

### tables-indexes/ — tables, constraints, indexes
- Tables: `case-sensitivity.md`, `common-data-types.md`, `table-constraints.md`,
  `temporary-tables.md`, `triggers.md`, `tablespaces-and-data-files.md`,
  `user-defined-types.md`, `unused-columns-and-alter-table.md`, `virtual-columns.md`,
  `read-only-tables-and-replicas.md`
- Indexes: `indexes-summary.md`, `btree-indexes.md`, `bitmap-indexes.md`,
  `composite-multicolumn-indexes.md`, `function-based-expression-indexes.md`,
  `invisible-indexes.md`, `index-organized-and-cluster-tables.md`, `partitioned-indexes.md`,
  `automatic-indexing.md`

### special-features/ — Oracle-specific features
- `character-sets-and-encoding.md`, `database-links-dblink-fdw.md`,
  `dbms-scheduler-and-lambda.md`, `external-tables-and-s3.md`, `inline-views.md`,
  `json-support.md`, `materialized-views.md`, `multitenant-architecture.md`,
  `resource-manager-and-dedicated-clusters.md`, `securefile-lobs-and-large-objects.md`,
  `views.md`, `xml-db-and-xml-type.md`, `log-miner-and-logging.md`

### ha-dr/ — high availability & disaster recovery
- `active-data-guard-and-replicas.md`, `rac-and-aurora-architecture.md`,
  `traffic-director-and-rds-proxy.md`, `data-pump-and-pg-dump-restore.md`,
  `flashback-database-and-snapshots.md`, `flashback-table-and-snapshots.md`,
  `rman-and-rds-snapshots.md`, `sqlloader-and-pg-dump-restore.md`

### configuration/
- `upgrades.md`, `alert-log-and-error-log.md`, `memory-sizing-and-buffers.md`,
  `instance-parameters-and-rds-parameter-groups.md`, `session-parameters.md`

### performance-tuning/
- `hints-and-query-planning.md`, `run-plans.md`, `table-statistics.md`

### security/
- `tde-and-encryption.md`, `roles.md`, `users.md`

### physical-storage/
- `table-partitioning-and-inheritance.md`, `sharding.md`

### monitoring/
- `vsviews-and-catalogs.md` (V$/data-dictionary → pg_catalog / statistics views / Performance
  Insights)

### quick-tips/
- `quick-tips.md` — fast checklist of common gotchas; start here for a high-level scan, then
  drill into the specific topic file.

## Cross-references
- Datatype mapping table: `engines/oracle-to-postgresql/datatype-map.yaml`
- Equivalence-testing methodology: `engines/oracle-to-postgresql/checks/equivalence-spec.md`
- Application-layer conversion rules (embedded SQL, drivers/ORM, error codes) for this pair: `engines/oracle-to-postgresql/app/` — used by the optional `app-modernization-orchestrator` module, not by DB-schema conversion.
