# Conversion log — MANUAL reconversions (DMS SC continuation)

ACCEPT and VERIFY objects keep the DMS SC conversion. This log covers the MANUAL objects
that were reconverted by hand (Kiro, construction skill), seeded from the source DDL with
the DMS SC output as a hint. Each file is in `code/<target schema>/` and was applied with
`apply-schema --code`. All of them are covered by `run-tests` (see
`03-validation/validation-summary.md`).

| Object | DMS SC action items | What DMS SC produced | Reconversion | Reference |
|---|---|---|---|---|
| `HumanResources.Employee` (table) | 7657, 7708 (column), 7679 | `organizationlevel` as a plain column plus a trigger that only rejects explicit values; the `GetLevel()` body left as a comment. Every row loaded with level NULL. | Column replaced by `GENERATED ALWAYS AS (count('/') - 1) STORED` over the varchar `organizationnode`; obsolete trigger dropped; index recreated. STORED because the column is indexed. | `target-baseline-aurora-postgresql-18.md` (computed columns); `datatype-map.yaml` (hierarchyid) |
| `HumanResources.uspUpdateEmployeeLogin` | 7644, 7657, 7706 | The only statement (the UPDATE) commented out; empty body. The procedure ran without error and changed nothing. | UPDATE restored with `organizationnode` as varchar; EXECUTE AS CALLER dropped. | `checks/non-portable-constructs.md` |
| `HumanResources.uspUpdateEmployeePersonalInfo` | 7644 | EXECUTE AS CALLER commented out, otherwise usable. | EXECUTE AS CALLER dropped (PG procedures run as the invoker by default). | `checks/non-portable-constructs.md` |
| `HumanResources.uspUpdateEmployeeHireInfo` | 7644, 7807, 7615, 7811 | `BEGIN TRAN` / `COMMIT` / `ROLLBACK` inside the exception block (not allowed in PG). | Transaction control removed: the PL/pgSQL block already gives all-or-nothing, and the caller owns the transaction. | `checks/non-portable-constructs.md` (transactions) |
| `HumanResources.dEmployee` (trigger) | 7809 | No output (INSTEAD OF DELETE on a table does not exist in PG). | `BEFORE DELETE` row trigger that raises the source message. | `checks/non-portable-constructs.md` §2 |
| `dbo.uspLogError` | 7811 ×2 | INSERT into ErrorLog commented out; body reads an undeclared `error_catch$ERROR_NUMBER`, so every call failed into its own handler. No error was ever logged. | Takes SQLSTATE / SQLERRM / procedure name from the caller (a PG procedure cannot read its caller's exception); returns without logging when called without them, like the source. The three HR procedures above pass them. Reconverted because the HR procedures call it. | `checks/non-portable-constructs.md` (TRY/CATCH, ERROR_*()) |

## MANUAL objects left open (`needs_human`)

| Object | Why it is left |
|---|---|
| `HumanResources.vJobCandidate`, `vJobCandidateEducation`, `vJobCandidateEmployment`; `Person.vAdditionalContactInfo` | XQuery `.value()` / `.nodes()` over typed XML (7708). Not on the target. Needs `xpath()` / `XMLTABLE` rewrites and a decision on the namespace handling. |
| `Person.iuPerson` (trigger) | XML DML `.modify(insert …)` (7833) has no PG equivalent. DMS SC applied a partial trigger. Needs a decision: rebuild the XML in PL/pgSQL or move the default into the application. |
| `HumanResources.HRResumeSchemaCollection`, `Person.*SchemaCollection` | XML schema collections (9994): PG has no typed XML. Drop, or validate in the application. |
| `Person.IX_vStateProvinceCountryRegion` | Index on an indexed view (7937). Plain view on PG; a materialized view only if the performance is needed. |
| `dbo.uspSearchCandidateResumes`, `uspGetEmployeeManagers`, `uspGetManagerEmployees`, `uspGetBillOfMaterials`, `uspGetWhereUsedProductID` | Outside the Person + HumanResources scope of this run. |

Also seen: DMS SC classified `dbo.uspPrintError` ACCEPT, but its body reads the same
undeclared `error_catch$…` variables, so it fails when called. It is outside this run's
scope; note it for the dbo schema.
