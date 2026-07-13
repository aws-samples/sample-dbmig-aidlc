---
name: sqlserver-to-mysql-playbook
description: Knowledge base for converting Microsoft SQL Server to MySQL (Aurora MySQL compatible), distilled from the AWS SQL-Server-to-Aurora-MySQL Migration Playbook into granular per-topic references. Use when converting or assessing a SQL Server construct for a MySQL target — datatypes, ANSI SQL (constraints, CTEs, views, window functions, GROUP BY), T-SQL (stored procedures, functions, triggers, cursors, error handling, MERGE, PIVOT, IDENTITY/sequences, collations, date/string functions, JSON/XML, full-text search, graph), indexes, management (SQL Agent, Database Mail, linked servers), HA/DR, configuration, performance tuning, physical storage, or security — and you need the MySQL equivalent, the conversion difficulty, and the workaround. The db-migration-inception and db-migration-construction skills consult this when the source is SQL Server and the target is MySQL. This is a reference index/router: load the specific topic file under references/ rather than reading everything.
---

# SQL Server → MySQL Playbook (reference index)

Granular conversion references distilled from the AWS *Microsoft SQL Server 2019 to Amazon
Aurora MySQL Migration Playbook*. **Reference only — test everything in a non-production
environment first.**

## How to use this skill

A **router**, not a document to read end-to-end. Given a SQL Server construct:
1. Find the topic below and open that single file under `references/`.
2. Each file states a **Conversion category** (Automatic / Assisted / Manual / Blocked),
   shows the SQL Server and MySQL forms, and lists conversion notes/gotchas.
3. Cite the file path in the conversion log / assessment for traceability.

Each chapter folder also has an `_index.md` with one-line summaries.

### SQL Server → MySQL specifics to keep in mind
- A SQL Server **schema** (e.g. `dbo`) maps to a **MySQL database**; identifiers are quoted
  with **backticks**; default storage engine is **InnoDB**; fold mixed-case to lower_case.
- **Case sensitivity**: SQL Server is usually case-insensitive (collation-dependent); MySQL
  depends on collation + `lower_case_table_names` — pick a collation matching the app.
- **IDENTITY → AUTO_INCREMENT** (one per table); `SCOPE_IDENTITY()`/`@@IDENTITY` →
  `LAST_INSERT_ID()`. **No MERGE** → `INSERT ... ON DUPLICATE KEY UPDATE`.
- **T-SQL → MySQL stored programs**; `TRY/CATCH` → `DECLARE ... HANDLER`.
- Common rewrites: `GETDATE()`→`NOW()`, `ISNULL`→`IFNULL`/`COALESCE`, `LEN`→`CHAR_LENGTH`,
  `TOP n`→`LIMIT`, `+` concat → `CONCAT()`, `CHARINDEX`→`LOCATE`.
- **`rowversion`/`timestamp`** is a binary row-version, NOT a datetime.

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
  `action-code.md`, `aws-dms.md`, `rds-proxy.md`, `rds-outposts.md`,
  `aurora-serverless.md`, `parallel-query.md`, `aurora-backtrack.md`

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
  `maintenance-plans.md`, `monitoring.md`, `resource-governor.md`, `linked-servers.md`,
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
