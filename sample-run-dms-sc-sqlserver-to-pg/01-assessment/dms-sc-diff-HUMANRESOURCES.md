# DMS SC diff vs live target — schema `HUMANRESOURCES` (target `adventureworks_humanresources`)

_Generated 2026-10-30T09:25:26Z · source MSSQL → target AURORA_POSTGRESQL_

- MATCH: **48**  ·  MISSING: **0**  ·  UNMATCHED (system-named): **2**  ·  EXTRA: **0**

## UNMATCHED by name (2) — system-named constraints/indexes

DMS SC assigns its own names to PK/UNIQUE/CHECK constraints and many indexes, so a name miss here does **not** mean the object is absent. Verify these by table + column set (a later capture/compare step will do this automatically).

| Object | Type | Apply status |
|---|---|---|
| `HumanResources.Namespaces` | NAMESPACES | - |
| `HumanResources.HRResumeSchemaCollection` | XML_SCHEMA_COLLECTION | - |

## MATCH

48 object(s) present and consistent. (Full per-object detail is in `dms-sc-map-<SCHEMA>.json`.)
