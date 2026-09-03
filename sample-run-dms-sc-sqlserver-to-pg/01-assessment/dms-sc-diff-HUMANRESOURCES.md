# DMS SC diff vs live target — schema `HUMANRESOURCES` (target `humanresources`)

_Generated 2026-09-02T07:40:24Z · source MSSQL → target AURORA_POSTGRESQL_

- MATCH: **44**  ·  MISSING: **2**  ·  UNMATCHED (system-named): **4**  ·  EXTRA: **1**

## MISSING on target (2) — converted by DMS SC but not applied

| Object | Type | Disposition | DMS SC apply status |
|---|---|---|---|
| `HumanResources.FK_EmployeeDepartmentHistory_Employee_BusinessEntityID` | CONSTRAINT | accept | ERROR |
| `HumanResources.dEmployee` | TRIGGER | manual | - |

## UNMATCHED by name (4) — system-named constraints/indexes

DMS SC assigns its own names to PK/UNIQUE/CHECK constraints and many indexes, so a name miss here does **not** mean the object is absent. Verify these by table + column set (a later capture/compare step will do this automatically).

| Object | Type | Apply status |
|---|---|---|
| `HumanResources.PK_EmployeeDepartmentHistory_BusinessEntityID_StartDate_DepartmentID` | CONSTRAINT | SUCCESS |
| `HumanResources.PK_EmployeePayHistory_BusinessEntityID_RateChangeDate` | CONSTRAINT | SUCCESS |
| `HumanResources.Namespaces` | NAMESPACES | - |
| `HumanResources.HRResumeSchemaCollection` | XML_SCHEMA_COLLECTION | - |

## EXTRA on target (1) — present live, not in the DMS SC map

| Name | Kind |
|---|---|
| `fn_tr_employee_biu` | routines |

## MATCH

44 object(s) present and consistent. (Full per-object detail is in `dms-sc-map-<SCHEMA>.json`.)
