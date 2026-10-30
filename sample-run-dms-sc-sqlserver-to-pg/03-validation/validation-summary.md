# Validation summary — PERSON + HUMANRESOURCES

## Data load (framework loader, `migrate-data`)

`pre-load-drop --apply` → `migrate-data` → `post-load-restore --apply`, per schema, into the
DMS SC target schemas `adventureworks_person` and `adventureworks_humanresources`.

| Schema | Tables | Rows | Secondary objects dropped / restored | `compare` |
|---|---|---|---|---|
| PERSON | 13 | 141,250 | 23 / 23 (13 FK, 8 index, 2 trigger) | 13/13 match |
| HUMANRESOURCES | 6 | 934 | 13 / 13 (6 FK, 5 index, 2 trigger) | 6/6 match |

Source types handled: `hierarchyid` (loaded as its string form, e.g. `/1/1/`), `xml`,
`geography` (PostGIS), `uniqueidentifier`, and `bit` into DMS SC's `numeric(1,0)` domain
`dbo.Flag`.

Row counts matching was **not** enough: after the load every `Employee.OrganizationLevel`
was NULL (DMS SC left the computed column unconverted). The `Employee` equivalence test
caught it; the column was reconverted and the test now passes.

## Equivalence tests (`run-tests`)

| Schema | Passed | Specs | Not tested |
|---|---|---|---|
| HUMANRESOURCES | 16/16 | vEmployee, vEmployeeDepartment, vEmployeeDepartmentHistory, uspUpdateEmployeeLogin, uspUpdateEmployeePersonalInfo, Employee (table), Department (defaults) | vJobCandidate ×3 (MANUAL, not on target), uspUpdateEmployeeHireInfo (flagged `test_mode: manual`: the source manages its own transaction) |
| PERSON | 3/3 | vStateProvinceCountryRegion, AddressType (defaults) | vAdditionalContactInfo (MANUAL, not on target) |

What the procedure cases prove (same net effect on both engines):

- `uspUpdateEmployeeLogin` moves an employee in the org tree; the node and the computed level
  change identically (level 3 → 3, then 3 → 2). A duplicate LoginID is rejected and logged
  once in ErrorLog on both engines.
- `uspUpdateEmployeePersonalInfo` accepts lowercase `m`/`f` (the CHECK constraints are
  case-insensitive on both) and rejects `X`, which is logged once on both. This needed the
  `dbo.uspLogError` reconversion: DMS SC's version never logged.

## VERIFY sign-off (`dbmig verify`)

| Schema | Verified | Failed | Pending |
|---|---|---|---|
| PERSON | 15 | 5 | 0 |
| HUMANRESOURCES | 8 | 0 | 0 |

- Equivalence-tested: vEmployee, vStateProvinceCountryRegion, CK_Employee_Gender,
  CK_Employee_MaritalStatus, CK_Person_PersonType, AddressType, Department.
- Catalog check: the other tables carry only 7826 (`DEFAULT getdate()` → `clock_timestamp()`)
  and 7831 (`newid()` → `uuid_generate_v4()`); the defaults are identical to the tested ones.
- **Failed:** the five XML indexes on `Person.Person` are not on the target. DMS SC emitted
  btree indexes on `xml` columns and the apply failed. PG has no XML index; add expression
  indexes on `xpath()` only where a query needs them.
- DBO has 2 pending (ErrorLog, AWBuildVersion): outside this run's scope.
