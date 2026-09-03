# DMS SC diff vs live target — schema `PERSON` (target `person`)

_Generated 2026-09-02T07:40:32Z · source MSSQL → target AURORA_POSTGRESQL_

- MATCH: **61**  ·  MISSING: **2**  ·  UNMATCHED (system-named): **13**  ·  EXTRA: **0**

## MISSING on target (2) — converted by DMS SC but not applied

| Object | Type | Disposition | DMS SC apply status |
|---|---|---|---|
| `Person.FK_BusinessEntityAddress_BusinessEntity_BusinessEntityID` | CONSTRAINT | accept | SUCCESS |
| `Person.FK_BusinessEntityContact_BusinessEntity_BusinessEntityID` | CONSTRAINT | accept | SUCCESS |

## UNMATCHED by name (13) — system-named constraints/indexes

DMS SC assigns its own names to PK/UNIQUE/CHECK constraints and many indexes, so a name miss here does **not** mean the object is absent. Verify these by table + column set (a later capture/compare step will do this automatically).

| Object | Type | Apply status |
|---|---|---|
| `Person.PK_BusinessEntityAddress_BusinessEntityID_AddressID_AddressTypeID` | CONSTRAINT | SUCCESS |
| `Person.PK_BusinessEntityContact_BusinessEntityID_PersonID_ContactTypeID` | CONSTRAINT | SUCCESS |
| `Person.PK_PersonPhone_BusinessEntityID_PhoneNumber_PhoneNumberTypeID` | CONSTRAINT | ERROR |
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

61 object(s) present and consistent. (Full per-object detail is in `dms-sc-map-<SCHEMA>.json`.)
