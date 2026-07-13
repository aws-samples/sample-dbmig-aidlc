# Customer-Specific Knowledge — HIGHEST PRECEDENCE (SQL Server → MySQL)

This folder holds knowledge about **this customer's own environment and application** for the
SQL Server → MySQL (Aurora MySQL) migration — conventions, datatype overrides,
collation/case-sensitivity expectations, and prior decisions. It is intentionally empty of
vendor content: you fill it in per engagement.

## Precedence rule

Content here **overrides** the general SQL Server→MySQL playbook references (`../tsql/`,
`../ansi-sql/`, etc.) wherever the two conflict. The conversion tooling injects every active
file in this folder at the **top** of each prompt bundle, labeled highest precedence, ahead
of the general playbook context.

## What belongs here (one Markdown file per topic; all optional)

- `environment.md` — Aurora MySQL version (8.0), `sql_mode`, `lower_case_table_names`,
  charset/collation (utf8mb4 + which collation for case sensitivity), storage engine.
- `naming-conventions.md` — identifier casing (SQL Server mixed-case → MySQL lower_case),
  schema→database mapping, object naming rules.
- `datatype-overrides.md` — mappings overriding the generic SQL Server → MySQL map (e.g. how
  `bit` flags map, `money` precision, `uniqueidentifier` as char(36) vs binary(16)).
- `collation.md` — case/accent sensitivity requirements per column.
- `application-constraints.md` — ORM/app expectations (AUTO_INCREMENT usage, queries that
  must not change shape).
- `decisions.md` — agreed redesigns for CLR, Service Broker, linked servers, rowversion,
  full-text search, MERGE.
- `forbidden.md` — features/patterns the customer disallows.

## Rules for writing these files

- Be specific and prescriptive — these are instructions applied at conversion time.
- Mark each overriding rule with "Override: …" so intent is unambiguous.
- Keep secrets out — this folder is committed with the repo.

## Status

No customer files are present yet. Add files here at the start of an engagement; until then,
conversion falls back entirely to the general SQL Server→MySQL playbook references.
