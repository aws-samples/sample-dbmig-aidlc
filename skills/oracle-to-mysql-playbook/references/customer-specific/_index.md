# Customer-Specific Knowledge — HIGHEST PRECEDENCE (Oracle → MySQL)

This folder holds knowledge about **this customer's own environment and application** for the
Oracle → MySQL (Aurora MySQL) migration — their conventions, datatype overrides, available
features, and prior decisions. It is intentionally empty of vendor content: you fill it in
per engagement.

## Precedence rule

Content here **overrides** the general MySQL playbook references (`../sql-plsql/`,
`../special-features/`, etc.) wherever the two conflict. The conversion tooling injects every
active file in this folder at the **top** of each prompt bundle, labeled highest precedence,
ahead of the general playbook context.

## What belongs here (one Markdown file per topic; all optional)

- `environment.md` — Aurora MySQL version (5.7/8.0), `sql_mode` (e.g. `only_full_group_by`,
  `STRICT_TRANS_TABLES`), `lower_case_table_names`, charset/collation (utf8mb4), storage engine.
- `naming-conventions.md` — identifier casing and object naming rules the customer requires.
- `datatype-overrides.md` — mappings that override the generic Oracle→MySQL map (e.g. how
  `NUMBER(1)` flags map; money columns; how DATE-only columns map).
- `application-constraints.md` — ORM/app expectations (AUTO_INCREMENT usage, allowed
  functions, queries that must not change shape).
- `decisions.md` — agreed redesigns for packages, sequences, MERGE, ROWID logic.
- `forbidden.md` — features/patterns the customer disallows.

## Rules for writing these files

- Be specific and prescriptive — these are instructions applied at conversion time.
- Mark each overriding rule with "Override: …" so intent is unambiguous.
- Keep secrets out — this folder is committed with the repo.

## Status

No customer files are present yet. Add files here at the start of an engagement; until then,
conversion falls back entirely to the general MySQL playbook references.
