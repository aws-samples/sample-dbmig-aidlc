# DMS SC import — triage for schema `DBO`

- Project: **aw-dms-sc-20261030**
- Source: **MSSQL** → Target: **AURORA_POSTGRESQL** (target schema `adventureworks_dbo`)
- Objects: **30** (storage=12, code=7, other=11)

## Disposition

| Disposition | Count | Meaning |
|---|---|---|
| ACCEPT | 22 | keep the DMS SC conversion as-is |
| VERIFY | 2 | keep, but prove with equivalence tests (gen-tests/run-tests) |
| MANUAL | 6 | must be reconverted (convert-code) |

> **Policy:** MANUAL = any action item of severity CRITICAL/HIGH, or an explicit "convert your source code manually" / method-stub instruction. VERIFY = any remaining action item (incl. `5444` ML/GenAI and LOW/MEDIUM advisories) or a GenAI-generated span. ACCEPT = no action items. Tune in `dbmig/dmssc/classify.py`.

## MANUAL — reconvert (6)

| Object | Type | GenAI | Applied | Action items |
|---|---|---|---|---|
| `dbo.uspGetBillOfMaterials` | PROCEDURE | - | SUCCESS | 7938/INFO Convert your source code manually. |
| `dbo.uspGetEmployeeManagers` | PROCEDURE | - | SUCCESS | 9996/CRITICAL Please submit report to developers.; 7708/CRITICAL Convert your source code manually.; 7938/INFO Convert your source code manually. |
| `dbo.uspGetManagerEmployees` | PROCEDURE | - | SUCCESS | 9996/CRITICAL Please submit report to developers.; 7708/CRITICAL Convert your source code manually.; 7938/INFO Convert your source code manually. |
| `dbo.uspGetWhereUsedProductID` | PROCEDURE | - | SUCCESS | 7938/INFO Convert your source code manually. |
| `dbo.uspLogError` | PROCEDURE | - | SUCCESS | 7811/CRITICAL Create a user-defined function to replace the unsupported function. |
| `dbo.uspSearchCandidateResumes` | PROCEDURE | - | SUCCESS | 7644/CRITICAL Convert your source code manually.; 7811/CRITICAL Create a user-defined function to replace the unsupported function.; 9996/CRITICAL Please submit report to developers.; 9997/INFO Verify the object name and conversion scope, grant the source database user access if needed, and reconver… |

## VERIFY — keep + prove (2)

| Object | Type | Verified | GenAI | Applied | Action items |
|---|---|---|---|---|---|
| `dbo.AWBuildVersion` | TABLE | ⏳ pending | - | SUCCESS | 7826/LOW Review the converted code to make sure that you set the default value of the DateTime variable. |
| `dbo.ErrorLog` | TABLE | ⏳ pending | - | SUCCESS | 7826/LOW Review the converted code to make sure that you set the default value of the DateTime variable. |

## ACCEPT — keep as-is (22)

| Object | Type | Applied |
|---|---|---|
| `dbo.PK_AWBuildVersion_SystemInformationID` | CONSTRAINT | SUCCESS |
| `dbo.PK_DatabaseLog_DatabaseLogID` | CONSTRAINT | SUCCESS |
| `dbo.PK_ErrorLog_ErrorLogID` | CONSTRAINT | SUCCESS |
| `dbo.uspPrintError` | PROCEDURE | SUCCESS |
| `dbo.ufnGetAccountingEndDate` | SQL_SCALAR_FUNCTION | SUCCESS |
| `dbo.ufnGetAccountingStartDate` | SQL_SCALAR_FUNCTION | SUCCESS |
| `dbo.ufnGetDocumentStatusText` | SQL_SCALAR_FUNCTION | SUCCESS |
| `dbo.ufnGetProductDealerPrice` | SQL_SCALAR_FUNCTION | SUCCESS |
| `dbo.ufnGetProductListPrice` | SQL_SCALAR_FUNCTION | SUCCESS |
| `dbo.ufnGetProductStandardCost` | SQL_SCALAR_FUNCTION | SUCCESS |
| `dbo.ufnGetPurchaseOrderStatusText` | SQL_SCALAR_FUNCTION | SUCCESS |
| `dbo.ufnGetSalesOrderStatusText` | SQL_SCALAR_FUNCTION | SUCCESS |
| `dbo.ufnGetStock` | SQL_SCALAR_FUNCTION | SUCCESS |
| `dbo.ufnLeadingZeros` | SQL_SCALAR_FUNCTION | SUCCESS |
| `dbo.ufnGetContactInformation` | SQL_TABLE_VALUED_FUNCTION | SUCCESS |
| `dbo.DatabaseLog` | TABLE | SUCCESS |
| `dbo.AccountNumber` | TYPE | SUCCESS |
| `dbo.Flag` | TYPE | SUCCESS |
| `dbo.Name` | TYPE | SUCCESS |
| `dbo.NameStyle` | TYPE | SUCCESS |
| `dbo.OrderNumber` | TYPE | SUCCESS |
| `dbo.Phone` | TYPE | SUCCESS |

