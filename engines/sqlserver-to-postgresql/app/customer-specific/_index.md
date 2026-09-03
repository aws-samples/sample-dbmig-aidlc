# Customer-Specific APPLICATION Knowledge — HIGHEST PRECEDENCE

This folder holds knowledge about **this customer's own application** as it is migrated from
a **SQL Server**-backed data layer to **PostgreSQL** — their frameworks, datasource/ORM configuration,
embedded-SQL conventions, error-handling patterns, prior decisions, and any deviations from
the generic app rules in `../app-sql-rules.md` and `../app-config.yaml`.

It is intentionally empty of vendor content: you fill it in per engagement. It is the
application-layer counterpart to the database playbook's
`skills/sqlserver-to-postgresql-playbook/references/customer-specific/`.

## Precedence rule

When the app-modernization skills inventory or edit application code, content in this folder
**overrides** the generic per-pair app rules (`../app-sql-rules.md`, `../app-config.yaml`)
**wherever the two conflict.** The generic rules are the default; customer-specific rules are
the authority for this customer. Mark each overriding rule with "Override:".

The `app-modernization-inception` and `app-modernization-construction` skills read every
`*.md` in this folder (except this `_index.md`) as the **top, highest-precedence** context
before the generic app rules — the same discipline the database side uses.

## What belongs here (one Markdown file per topic; all optional)

- `frameworks.md` — the app's language/framework/ORM and versions (e.g. Java/Spring +
  Hibernate, .NET + EF, Python + SQLAlchemy) and the exact target driver/dialect to use for PostgreSQL.
- `datasource-config.md` — connection/datasource settings the customer requires (driver
  class, URL shape, pool, SSL) for PostgreSQL.
- `embedded-sql-conventions.md` — how embedded SQL is written and must be transformed
  (named vs positional params, quoting/identifier case, dialect functions to prefer/avoid).
- `error-handling.md` — mapping of SQL Server error codes/SQLSTATEs the app checks to their PostgreSQL
  equivalents; retry/exception conventions that must be preserved.
- `result-set-typing.md` — result-set/column type expectations the app relies on
  (e.g. numeric/boolean/date handling) that differ under PostgreSQL.
- `decisions.md` — engagement decisions already approved or deferred.
- `forbidden.md` — patterns/libraries/features the customer explicitly disallows.

## Rules for writing these files

- Be specific and prescriptive — these are instructions applied per code site, not background.
- State each rule so it can be applied directly to a single embedded-SQL / config / call site.
- When a rule overrides the generic app rules, say so explicitly ("Override: …").
