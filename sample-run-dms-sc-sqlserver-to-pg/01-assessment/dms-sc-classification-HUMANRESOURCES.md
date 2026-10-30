# DMS SC import — triage for schema `HUMANRESOURCES`

- Project: **aw-dms-sc-20261030**
- Source: **MSSQL** → Target: **AURORA_POSTGRESQL** (target schema `adventureworks_humanresources`)
- Objects: **50** (storage=39, code=10, other=1)

## Disposition

| Disposition | Count | Meaning |
|---|---|---|
| ACCEPT | 33 | keep the DMS SC conversion as-is |
| VERIFY | 8 | keep, but prove with equivalence tests (gen-tests/run-tests) |
| MANUAL | 9 | must be reconverted (convert-code) |

> **Policy:** MANUAL = any action item of severity CRITICAL/HIGH, or an explicit "convert your source code manually" / method-stub instruction. VERIFY = any remaining action item (incl. `5444` ML/GenAI and LOW/MEDIUM advisories) or a GenAI-generated span. ACCEPT = no action items. Tune in `dbmig/dmssc/classify.py`.

## MANUAL — reconvert (9)

| Object | Type | GenAI | Applied | Action items |
|---|---|---|---|---|
| `HumanResources.uspUpdateEmployeeHireInfo` | PROCEDURE | - | SUCCESS | 7644/CRITICAL Convert your source code manually.; 7807/CRITICAL Convert your source code manually.; 7615/CRITICAL Revise your code to move transaction control to the application side and try again.; 7811/CRITICAL Create a user-defined function to replace the unsupported function. |
| `HumanResources.uspUpdateEmployeeLogin` | PROCEDURE | - | SUCCESS | 7644/CRITICAL Convert your source code manually.; 7657/CRITICAL Convert your source code manually to make sure that you store data of the hierarchyid data type using a compatible type in PostgreSQL or a composite type.; 7706/HIGH Convert your source code manually to make sure that you use a compatib… |
| `HumanResources.uspUpdateEmployeePersonalInfo` | PROCEDURE | - | SUCCESS | 7644/CRITICAL Convert your source code manually. |
| `HumanResources.Employee` | TABLE | - | SUCCESS | 7657/CRITICAL Convert your source code manually to make sure that you store data of the hierarchyid data type using a compatible type in PostgreSQL or a composite type.; 7708/CRITICAL Convert your source code manually.; 7679/INFO Review the converted code and change it where necessary.; 7831/INFO Re… |
| `HumanResources.dEmployee` | TRIGGER | - | - | 7809/CRITICAL Convert your source code manually. |
| `HumanResources.vJobCandidate` | VIEW | - | SUCCESS | 9997/INFO Verify the object name and conversion scope, grant the source database user access if needed, and reconvert. Review runtime-built or unsupported references manually.; 7708/CRITICAL Convert your source code manually. |
| `HumanResources.vJobCandidateEducation` | VIEW | - | SUCCESS | 7708/CRITICAL Convert your source code manually. |
| `HumanResources.vJobCandidateEmployment` | VIEW | - | SUCCESS | 7708/CRITICAL Convert your source code manually. |
| `HumanResources.HRResumeSchemaCollection` | XML_SCHEMA_COLLECTION | - | - | 9994/CRITICAL Perform manual conversion. |

## VERIFY — keep + prove (8)

| Object | Type | Verified | GenAI | Applied | Action items |
|---|---|---|---|---|---|
| `HumanResources.CK_Employee_Gender` | CONSTRAINT | ✅ verified | - | SUCCESS | 7795/INFO Review the converted code to make sure that it compares strings correctly. |
| `HumanResources.CK_Employee_MaritalStatus` | CONSTRAINT | ✅ verified | - | SUCCESS | 7795/INFO Review the converted code to make sure that it compares strings correctly. |
| `HumanResources.Department` | TABLE | ✅ verified | - | SUCCESS | 7826/LOW Review the converted code to make sure that you set the default value of the DateTime variable. |
| `HumanResources.EmployeeDepartmentHistory` | TABLE | ✅ verified | - | SUCCESS | 7826/LOW Review the converted code to make sure that you set the default value of the DateTime variable. |
| `HumanResources.EmployeePayHistory` | TABLE | ✅ verified | - | SUCCESS | 7826/LOW Review the converted code to make sure that you set the default value of the DateTime variable. |
| `HumanResources.JobCandidate` | TABLE | ✅ verified | - | SUCCESS | 7826/LOW Review the converted code to make sure that you set the default value of the DateTime variable. |
| `HumanResources.Shift` | TABLE | ✅ verified | - | SUCCESS | 7826/LOW Review the converted code to make sure that you set the default value of the DateTime variable. |
| `HumanResources.vEmployee` | VIEW | ✅ verified | - | ERROR | 7795/INFO Review the converted code to make sure that it compares strings correctly. |

## ACCEPT — keep as-is (33)

| Object | Type | Applied |
|---|---|---|
| `HumanResources.CK_EmployeeDepartmentHistory_EndDate` | CONSTRAINT | SUCCESS |
| `HumanResources.CK_EmployeePayHistory_PayFrequency` | CONSTRAINT | SUCCESS |
| `HumanResources.CK_EmployeePayHistory_Rate` | CONSTRAINT | SUCCESS |
| `HumanResources.CK_Employee_BirthDate` | CONSTRAINT | SUCCESS |
| `HumanResources.CK_Employee_HireDate` | CONSTRAINT | SUCCESS |
| `HumanResources.CK_Employee_SickLeaveHours` | CONSTRAINT | SUCCESS |
| `HumanResources.CK_Employee_VacationHours` | CONSTRAINT | SUCCESS |
| `HumanResources.FK_EmployeeDepartmentHistory_Department_DepartmentID` | CONSTRAINT | SUCCESS |
| `HumanResources.FK_EmployeeDepartmentHistory_Employee_BusinessEntityID` | CONSTRAINT | SUCCESS |
| `HumanResources.FK_EmployeeDepartmentHistory_Shift_ShiftID` | CONSTRAINT | SUCCESS |
| `HumanResources.FK_EmployeePayHistory_Employee_BusinessEntityID` | CONSTRAINT | SUCCESS |
| `HumanResources.FK_Employee_Person_BusinessEntityID` | CONSTRAINT | ERROR |
| `HumanResources.FK_JobCandidate_Employee_BusinessEntityID` | CONSTRAINT | SUCCESS |
| `HumanResources.PK_Department_DepartmentID` | CONSTRAINT | SUCCESS |
| `HumanResources.PK_EmployeeDepartmentHistory_BusinessEntityID_StartDate_DepartmentID` | CONSTRAINT | SUCCESS |
| `HumanResources.PK_EmployeePayHistory_BusinessEntityID_RateChangeDate` | CONSTRAINT | SUCCESS |
| `HumanResources.PK_Employee_BusinessEntityID` | CONSTRAINT | SUCCESS |
| `HumanResources.PK_JobCandidate_JobCandidateID` | CONSTRAINT | SUCCESS |
| `HumanResources.PK_Shift_ShiftID` | CONSTRAINT | SUCCESS |
| `HumanResources.AK_Department_Name` | INDEX | SUCCESS |
| `HumanResources.AK_Employee_LoginID` | INDEX | SUCCESS |
| `HumanResources.AK_Employee_NationalIDNumber` | INDEX | SUCCESS |
| `HumanResources.AK_Employee_rowguid` | INDEX | SUCCESS |
| `HumanResources.AK_Shift_Name` | INDEX | SUCCESS |
| `HumanResources.AK_Shift_StartTime_EndTime` | INDEX | SUCCESS |
| `HumanResources.IX_EmployeeDepartmentHistory_DepartmentID` | INDEX | SUCCESS |
| `HumanResources.IX_EmployeeDepartmentHistory_ShiftID` | INDEX | SUCCESS |
| `HumanResources.IX_Employee_OrganizationLevel_OrganizationNode` | INDEX | SUCCESS |
| `HumanResources.IX_Employee_OrganizationNode` | INDEX | SUCCESS |
| `HumanResources.IX_JobCandidate_BusinessEntityID` | INDEX | SUCCESS |
| `HumanResources.Namespaces` | NAMESPACES | - |
| `HumanResources.vEmployeeDepartment` | VIEW | ERROR |
| `HumanResources.vEmployeeDepartmentHistory` | VIEW | ERROR |

