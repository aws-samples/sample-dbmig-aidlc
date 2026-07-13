# Customer-Specific Knowledge — HIGHEST PRECEDENCE

This folder holds knowledge about **this customer's own environment and application** —
their conventions, constraints, prior decisions, and any deviations from the generic AWS
playbook. It is intentionally empty of vendor content: you fill it in per engagement.

## Precedence rule

When converting or assessing objects, content in this folder **overrides** the general
playbook references (`../sql-plsql/`, `../tables-indexes/`, `../special-features/`, etc.)
**wherever the two conflict.** The general playbook is the default; customer-specific rules
are the authority for this customer.

The conversion tooling enforces this: `dbmig convert-schema` / `convert-code` inject every
file in this folder at the **top** of each prompt bundle, labeled as highest precedence,
ahead of the general playbook context. The `db-migration-construction` skill applies the
same ordering when it converts.

## What belongs here

Create one Markdown file per topic. Suggested files (all optional):

- `environment.md` — target setup: Aurora PostgreSQL version, extensions available
  (e.g. `pg_trgm`, `postgis`, `pg_cron`), instance class, network/SSL, region.
- `naming-conventions.md` — identifier casing, schema layout, table/column/constraint/index
  naming rules the customer requires (may differ from the playbook's lower_case default).
- `datatype-overrides.md` — customer mappings that override the generic datatype map
  (e.g. "Oracle `NUMBER(1)` flags map to `boolean`", "money columns use `numeric(19,4)`").
- `application-constraints.md` — app/ORM expectations (Hibernate dialect, sequence usage,
  case-sensitivity assumptions, queries that must not change shape).
- `decisions.md` — engagement decisions already made (what was deferred, what was approved,
  agreed redesigns for packages / ROWID logic / autonomous transactions).
- `forbidden.md` — things the customer explicitly disallows (extensions, features, patterns).

## Rules for writing these files

- Be specific and prescriptive — these are instructions, not background reading.
- State each rule so it can be applied directly to a single object's conversion.
- When a rule overrides the playbook, say so explicitly ("Override: …") so the intent is
  unambiguous at conversion time.
- Keep secrets out — this folder is committed with the repo. Reference systems by name, not
  credentials.

## Status

No customer files are present yet. Add files here at the start of an engagement. Until then,
conversion falls back entirely to the general playbook references.
