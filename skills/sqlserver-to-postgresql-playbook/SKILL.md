---
name: sqlserver-to-postgresql-playbook
description: Knowledge base for converting Microsoft SQL Server to PostgreSQL (Aurora PostgreSQL compatible), distilled from the AWS SQL-Server-to-Aurora-PostgreSQL Migration Playbook into granular per-topic references. Use when converting or assessing a SQL Server construct for a PostgreSQL target — datatypes, ANSI SQL (constraints, CTEs, views, window functions, temporal tables), T-SQL (stored procedures, functions, triggers, cursors, dynamic SQL, error handling, MERGE, PIVOT, IDENTITY/sequences, collations, CAST/CONVERT, JSON/XML, Service Broker, CLR), indexes, management (SQL Agent, Database Mail, linked servers), HA/DR, configuration, performance tuning, physical storage (columnstore, partitioning), or security — and you need the PostgreSQL equivalent, the conversion difficulty, and the workaround. The db-migration-inception and db-migration-construction skills consult this when the source engine is SQL Server. This is a reference index/router: load the specific topic file under references/ rather than reading everything.
---

# SQL Server → PostgreSQL Playbook (reference index)

Granular conversion references distilled from the AWS *Microsoft SQL Server 2019 to Amazon
Aurora PostgreSQL Migration Playbook*. **Reference only — test everything in a non-production
environment first.**

## How to use this skill

A **router**, not a document to read end-to-end. Given a SQL Server construct:
1. Find the topic below and open that single file under `references/`.
2. Each file states a **Conversion category** (Automatic / Assisted / Manual / Blocked),
   shows the SQL Server and PostgreSQL forms, and lists conversion notes/gotchas.
3. Cite the file path in the conversion log / assessment for traceability.

Each chapter folder also has an `_index.md` with one-line summaries.

### SQL Server specifics to keep in mind
- A SQL Server **schema** (e.g. `dbo`) maps to a **PostgreSQL schema** (objects are
  `[schema].[object]`). Identifiers: brackets/`"` → fold mixed-case to lower_case in PG.
- **Case sensitivity**: SQL Server is usually case-insensitive (collation-dependent);
  PostgreSQL is case-sensitive — verify string comparisons (consider `citext`/`lower()`).
- **No CLUSTERED index** in PostgreSQL; **IDENTITY** → `GENERATED AS IDENTITY`/sequences;
  **T-SQL** → PL/pgSQL; **`rowversion`** is binary, not a datetime.
- Common rewrites: `GETDATE()`→`now()`, `ISNULL`→`COALESCE`, `LEN`→`length`, `TOP n`→`LIMIT`,
  `+` string concat → `||`, `@@IDENTITY`/`SCOPE_IDENTITY()` → `RETURNING`/`currval`.

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
  `aurora-serverless-v1.md`

### ansi-sql/ — ANSI SQL features
- `case-sensitivity.md`, `constraints.md`, `creating-tables.md`,
  `common-table-expressions.md`, `data-types.md`, `derived-tables.md`, `group-by.md`,
  `table-join.md`, `temporal-tables.md`, `views.md`, `window-functions.md`

### tsql/ — T-SQL features (the bulk of code conversion)
- Functions/queries: `cast-and-convert.md`, `string-functions.md`,
  `date-time-functions.md`, `merge.md`, `pivot-unpivot.md`, `top-fetch.md`,
  `delete-update-from.md`, `json-and-xml.md`
- Procedural: `stored-procedures.md`, `user-defined-functions.md`, `triggers.md`,
  `cursors.md`, `dynamic-sql.md`, `flow-control.md`, `error-handling.md`, `transactions.md`
- Schema/types: `databases-and-schemas.md`, `identity-and-sequences.md`,
  `user-defined-types.md`, `synonyms.md`, `collations.md`
- Advanced: `service-broker.md`, `common-language-runtime.md`, `full-text-search.md`,
  `graph-features.md`

### indexes/
- `indexes.md` (clustered/non-clustered/filtered/covering/computed → PG B-tree/partial/
  expression/INCLUDE/BRIN; no CLUSTERED)

### management/ — operational features
- `sql-server-agent.md`, `alerting.md`, `database-mail.md`, `etl.md`, `export-import.md`,
  `server-logs.md`, `maintenance-plans.md`, `monitoring.md`, `resource-governor.md`,
  `linked-servers.md`, `scripting.md`

### ha-dr/
- `backup-and-restore.md`, `high-availability-essentials.md`

### configuration/
- `upgrades.md`, `session-options.md`, `database-options.md`, `server-options.md`

### performance-tuning/
- `run-plans.md`, `query-hints-and-plan-guides.md`, `managing-statistics.md`

### physical-storage/
- `columnstore-indexes.md`, `indexed-and-materialized-views.md`, `partitioning.md`

### security/
- `column-encryption.md`, `data-control-language.md`, `tde.md`, `users-and-roles.md`

### deprecated-features/
- `deprecated-features.md` — SQL Server 2019 deprecated features + replacements

### quick-tips/
- `quick-tips.md` — fast checklist of common gotchas; start here, then drill into the topic file.

## Cross-references
- Datatype mapping: `engines/sqlserver-to-postgresql/datatype-map.yaml`
- Equivalence-testing methodology: `engines/sqlserver-to-postgresql/checks/equivalence-spec.md`
