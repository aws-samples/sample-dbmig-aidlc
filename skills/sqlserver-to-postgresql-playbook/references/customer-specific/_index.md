# Customer-Specific Knowledge — HIGHEST PRECEDENCE (SQL Server → PostgreSQL)

This folder holds knowledge about **this customer's own environment and application** for the
SQL Server → PostgreSQL (Aurora PostgreSQL) migration — their conventions, datatype
overrides, collation/case-sensitivity expectations, and prior decisions. It is intentionally
empty of vendor content: you fill it in per engagement.

## Precedence rule

Content here **overrides** the general SQL Server playbook references (`../tsql/`,
`../ansi-sql/`, etc.) wherever the two conflict. The conversion tooling injects every active
file in this folder at the **top** of each prompt bundle, labeled highest precedence, ahead
of the general playbook context.

## What belongs here (one Markdown file per topic; all optional)

- `environment.md` — target Aurora PostgreSQL version, available extensions (`citext`,
  `uuid-ossp`, `postgis`, `pg_trgm`), encoding/collation, schema layout.
- `naming-conventions.md` — identifier casing (SQL Server mixed-case → PostgreSQL lower_case),
  object naming rules.
- `datatype-overrides.md` — mappings that override the generic SQL Server → PostgreSQL map
  (e.g. how `bit` flags map, `money` precision, `datetime` precision, `uniqueidentifier`).
- `collation.md` — case-insensitivity requirements (which columns must stay case-insensitive
  → `citext` or `lower()`), accent sensitivity.
- `application-constraints.md` — ORM/app expectations (IDENTITY usage, queries that must not
  change shape, case-insensitive lookups).
- `decisions.md` — agreed redesigns for CLR, Service Broker, linked servers, rowversion,
  hierarchyid, full-text search.
- `forbidden.md` — features/patterns the customer disallows.

## Rules for writing these files

- Be specific and prescriptive — these are instructions applied at conversion time.
- Mark each overriding rule with "Override: …" so intent is unambiguous.
- Keep secrets out — this folder is committed with the repo.

## Status

No customer files are present yet. Add files here at the start of an engagement; until then,
conversion falls back entirely to the general SQL Server playbook references.
