---
name: sqlserver-to-mysql-playbook
description: Knowledge base for converting Microsoft SQL Server to MySQL (Aurora MySQL compatible), distilled from the AWS SQL-Server-to-Aurora-MySQL Migration Playbook into granular per-topic references and refreshed for Aurora MySQL 8.4 and Aurora MySQL 3 (MySQL 8.0) targets (validated on 8.4.8 and 3.13.0). Use when converting or assessing a SQL Server construct for a MySQL target — datatypes, ANSI SQL (constraints, CTEs, views, window functions, GROUP BY), T-SQL (stored procedures, functions, triggers, cursors, error handling, MERGE, PIVOT, IDENTITY/sequences, collations, date/string functions, JSON/XML, full-text search, graph), indexes, management (SQL Agent, Database Mail, linked servers), HA/DR, configuration, performance tuning, physical storage, or security — and you need the MySQL equivalent, the conversion difficulty, and the workaround. The db-migration-inception and db-migration-construction skills consult this when the source is SQL Server and the target is MySQL. This is a reference index/router: load the specific topic file under references/ rather than reading everything.
---

# SQL Server → MySQL Playbook (reference index)

Granular conversion references distilled from the AWS *Microsoft SQL Server 2019 to Amazon
Aurora MySQL Migration Playbook*. **Reference only — test everything in a non-production
environment first.**

## Target version baseline: Aurora MySQL 8.4 (and 3)

The AWS playbook was written for Aurora MySQL 2 (MySQL 5.7). Every file here has been reviewed
for **Aurora MySQL 8.4** (primary target) and **Aurora MySQL 3** (MySQL 8.0) and validated on two
live clusters (8.4.8 and 3.13.0) on 2026-10-29. Each topic file carries a
`Reviewed for Aurora MySQL 8.4 and 3` line naming what changed; statements marked *verified*
were executed on both clusters unless a version is named.

- **Start with the shared baseline**
  `../oracle-to-mysql-playbook/references/target-baseline-aurora-mysql.md`: which version to
  target, conversion defaults, behavior differences that bite (Aurora's minimal default
  `sql_mode`, case/accent-insensitive NO PAD collation, `LENGTH` in bytes, `GROUP_CONCAT`
  truncation), 8.4-vs-3 differences, AWS integrations, and tooling support (DMS SC targets
  Aurora MySQL 8.0.32 only).
- 5.7-era statements in the original playbook ("no CTEs", "no window functions", CHECK
  constraints parsed but ignored, no roles, Aurora Serverless v1, Performance Insights) are
  superseded: CTEs, window functions, enforced CHECK constraints and roles all exist on 3 and
  8.4; Serverless v1 is retired (use v2); Performance Insights is replaced by CloudWatch
  Database Insights. The topic files keep the old workarounds only in marked legacy sections.
- Silent traps verified on both versions: `ON DELETE SET DEFAULT` behaves as `RESTRICT`; a
  column-level `REFERENCES` clause creates no foreign key; `ENGINE=FEDERATED` silently becomes
  InnoDB; `'a' + 'b'` returns `0`; temporary tables cannot be referenced twice in one statement.
- The toolkit's `engines/sqlserver-to-mysql/engine.yaml` says `default_version: "8.0"`. Record
  the chosen version (8.4 or 3.x) in `customer-specific/environment.md`.

## How to use this skill

A **router**, not a document to read end-to-end. Given a SQL Server construct:
1. Find the topic below and open that single file under `references/`.
2. Each file states a **Conversion category** (Automatic / Assisted / Manual / Blocked),
   shows the SQL Server and MySQL forms, and lists conversion notes/gotchas.
3. Cite the file path in the conversion log / assessment for traceability.

Each chapter folder also has an `_index.md` with one-line summaries.

### SQL Server → MySQL specifics to keep in mind
- A SQL Server **schema** (e.g. `dbo`) maps to a **MySQL database**; identifiers are quoted
  with **backticks**; default storage engine is **InnoDB**; fold mixed-case to lower_case
  (toolkit convention).
- **Case sensitivity**: SQL Server is usually case-insensitive (collation-dependent). On Aurora
  MySQL, `lower_case_table_names=0` (database and table names are case-sensitive, fixed at
  cluster creation) and the default data collation `utf8mb4_0900_ai_ci` is case- *and*
  accent-insensitive and NO PAD (trailing spaces matter, unlike SQL Server) — pick a collation
  matching the app.
- **IDENTITY → AUTO_INCREMENT** (one per table, must lead some index); `SCOPE_IDENTITY()`/`@@IDENTITY` →
  `LAST_INSERT_ID()`. **No MERGE and no sequences in any version** → `INSERT ... ON DUPLICATE KEY UPDATE`
  (row-alias form) and `AUTO_INCREMENT` or a sequence table.
- **T-SQL → MySQL stored programs**; `TRY/CATCH` → `DECLARE ... HANDLER`; no parameter
  defaults, named arguments or overloading; table-valued parameters → JSON + `JSON_TABLE`.
- **8.4 only**: foreign keys must reference a full unique key, `AUTO_INCREMENT` on
  `FLOAT`/`DOUBLE` is rejected, `require_secure_transport=ON`, new users get
  `caching_sha2_password`, `MASTER`/`SLAVE` replication statements are removed.
- Common rewrites: `GETDATE()`→`NOW()`, `ISNULL`→`IFNULL`/`COALESCE`, `LEN`→`CHAR_LENGTH`,
  `TOP n`→`LIMIT`, `+` concat → `CONCAT()`, `CHARINDEX`→`LOCATE`.
- **`rowversion`/`timestamp`** is a binary row-version, NOT a datetime.

### Conversion categories
- **Automatic** — direct equivalent, low risk.
- **Assisted** — mechanical rewrite with a known pattern.
- **Manual** — needs redesign / human judgment.
- **Blocked** — no supported path; flag to the user and find an architectural alternative.

## How this playbook is consumed

Only the parts below are read by a phase; keep them current first.

| Consumer | What it reads |
|---|---|
| Construction and Validation (automatic) | `dbmig` writes the shared `_context-<phase>.md` with: the selected sections of `../oracle-to-mysql-playbook/references/target-baseline-aurora-mysql.md` (configured by `conversion.target_baseline` in `engines/sqlserver-to-mysql/engine.yaml`), `quick-tips/quick-tips.md` in full, and the `_index.md` of `ansi-sql/`, `indexes/`, `physical-storage/`, `deprecated-features/` (schema); `tsql/`, `ansi-sql/`, `deprecated-features/` (code). The test context gets the baseline's behavior-differences section. |
| Construction (on demand) | The topic file named in each detected-construct hint (`— see skills/sqlserver-to-mysql-playbook/references/…`); the converter cites it in `conversion-log.md`, and `./dbmig status` counts the citations. |
| DMS SC ingest | `tools/action-code.md` to judge DMS SC action items. |
| Operations | `tools/aws-dms.md`, `tools/rds-proxy.md`, `ha-dr/`, `configuration/`, `management/monitoring.md`, `performance-tuning/`. |
| Reference only | the other `tools/` files, `security/` and the rest of `management/`. No phase reads these; refresh them only when someone needs them. |

## Precedence: customer-specific knowledge wins

`references/customer-specific/` holds this customer's environment/application rules and has
**higher precedence than every general reference**. The conversion tooling injects active
files from that folder at the top of each prompt bundle. Consult `customer-specific/` first,
then fall back to the general references. See `customer-specific/_index.md`.

## Topic map

### customer-specific/ — HIGHEST PRECEDENCE (this customer's environment/application)
- Populated per engagement; overrides everything below on conflict.

### Shared baseline — read first
- `../oracle-to-mysql-playbook/references/target-baseline-aurora-mysql.md` (Aurora MySQL 8.4 / 3).

### tools/ — migration tooling
- `native-tools.md` (informational; dbmig uses Python drivers), `aws-sct.md`,
  `action-code.md`, `aws-dms.md`, `rds-proxy.md`, `rds-outposts.md`,
  `aurora-serverless.md` (Serverless v2), `parallel-query.md`, `aurora-backtrack.md`

### ansi-sql/ — ANSI SQL features
- `ansi-sql.md`, `case-sensitivity.md`, `constraints.md`, `creating-tables.md`, `cte.md`,
  `data-types.md`, `group-by.md`, `table-join.md`, `temporary-tables.md`, `views.md`,
  `window-functions.md`

### tsql/ — T-SQL features (the bulk of code conversion)
- Functions/queries: `string-functions.md`, `datetime.md`, `merge.md`, `pivot.md`,
  `top-fetch.md`, `delete-update.md`, `xml.md`
- Procedural: `stored-procedures.md`, `udf.md`, `triggers.md`, `cursors.md`,
  `flow-control.md`, `error-handling.md`, `transactions.md`
- Schema/types: `databases-schemas.md`, `identity-sequences.md`, `udt.md`, `synonyms.md`,
  `collations.md`
- Advanced: `full-text-search.md`, `graph.md`, `managing-statistics.md`

### indexes/
- `indexes.md` (clustered/non-clustered/filtered/covering/computed → MySQL InnoDB PK
  clustering, secondary, prefix, generated-column indexes)

### management/ — operational features
- `agent.md`, `alerting.md`, `database-mail.md`, `etl.md`, `server-logs.md`,
  `maintenance-plans.md`, `monitoring.md` (CloudWatch Database Insights), `resource-governor.md`, `linked-servers.md`,
  `scripting.md`

### ha-dr/
- `backup-restore.md`, `essentials.md`, `hadr.md`

### configuration/
- `upgrades.md`, `session-options.md`, `database-options.md`, `server-options.md`

### performance-tuning/
- `plans.md`, `query-hints.md`

### physical-storage/
- `storage.md`

### security/
- `column-encryption.md`, `data-control-language.md`, `transparent-data-encryption.md`,
  `users-roles.md`, `encrypted-connections.md`

### deprecated-features/
- `deprecated-features.md` — SQL Server 2019 deprecated features + replacements

### quick-tips/
- `quick-tips.md` — fast checklist of common gotchas; start here, then drill into the topic file.

## Cross-references
- Datatype mapping: `engines/sqlserver-to-mysql/datatype-map.yaml`
- Equivalence-testing methodology: `engines/sqlserver-to-mysql/checks/equivalence-spec.md`
- Application-layer conversion rules (embedded SQL, drivers/ORM, error codes) for this pair: `engines/sqlserver-to-mysql/app/` — used by the optional `app-modernization-orchestrator` module, not by DB-schema conversion.
