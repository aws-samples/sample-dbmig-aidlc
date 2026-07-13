# EXAMPLE — Datatype & convention overrides (template)

> This is an EXAMPLE/template, not active rules. Copy it to a real file (e.g.
> `datatype-overrides.md`) and edit, or delete it. Files in this folder take precedence
> over the general playbook when they conflict. Mark each overriding rule with "Override:".

## Identifiers
- Override: keep the customer's existing lower_snake_case table names verbatim; do NOT
  re-case or pluralize.
- Constraint naming: `pk_<table>`, `fk_<table>_<ref>`, `uq_<table>_<cols>`, `ix_<table>_<cols>`.

## Datatype overrides (take precedence over engines/.../datatype-map.yaml)
- Override: Oracle `NUMBER(1)` used as a flag → PostgreSQL `boolean` (app stores 0/1).
- Override: monetary columns → `numeric(19,4)` (never `double precision`).
- Override: `DATE` columns that store date-only (time always 00:00:00) → `date`, not
  `timestamp` — confirmed with the app team for tables `INVOICE`, `LEDGER`.

## Extensions available on the target
- `pg_trgm` and `pgcrypto` are installed and approved. `postgis` is NOT available — do not
  emit geometry types; flag any `SDO_GEOMETRY` for redesign.

## Application constraints
- The app uses Hibernate with sequences; convert Oracle sequences to PostgreSQL `sequence`
  objects (not `GENERATED AS IDENTITY`) so the existing dialect keeps working.

## Forbidden
- Do not use `SERIAL`; use explicit sequences per the rule above.
- Do not add triggers to enforce rules that the application already enforces.
