# DMS SC diff vs live target — schema `PERSON` (target `adventureworks_person`)

_Generated 2026-10-30T09:25:13Z · source MSSQL → target AURORA_POSTGRESQL_

- MATCH: **65**  ·  MISSING: **1**  ·  UNMATCHED (system-named): **10**  ·  EXTRA: **0**

## MISSING on target (1) — converted by DMS SC but not applied

| Object | Type | Disposition | DMS SC apply status |
|---|---|---|---|
| `Person.FK_StateProvince_SalesTerritory_TerritoryID` | CONSTRAINT | accept | ERROR |

## UNMATCHED by name (10) — system-named constraints/indexes

DMS SC assigns its own names to PK/UNIQUE/CHECK constraints and many indexes, so a name miss here does **not** mean the object is absent. Verify these by table + column set (a later capture/compare step will do this automatically).

| Object | Type | Apply status |
|---|---|---|
| `Person.IX_vStateProvinceCountryRegion` | INDEX | - |
| `Person.PXML_Person_AddContact` | INDEX | ERROR |
| `Person.PXML_Person_Demographics` | INDEX | ERROR |
| `Person.XMLPATH_Person_Demographics` | INDEX | ERROR |
| `Person.XMLPROPERTY_Person_Demographics` | INDEX | ERROR |
| `Person.XMLVALUE_Person_Demographics` | INDEX | ERROR |
| `Person.Namespaces` | NAMESPACES | - |
| `Person.Namespaces` | NAMESPACES | - |
| `Person.AdditionalContactInfoSchemaCollection` | XML_SCHEMA_COLLECTION | - |
| `Person.IndividualSurveySchemaCollection` | XML_SCHEMA_COLLECTION | - |

## MATCH

65 object(s) present and consistent. (Full per-object detail is in `dms-sc-map-<SCHEMA>.json`.)
