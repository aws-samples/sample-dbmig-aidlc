# Migration report — adventureworks-hr-person

_Last updated: 2026-09-02 07:40:35Z · maintained automatically by dbmig._

This report is refreshed after each phase. It summarizes what has been done, the current state, and what you should be aware of or do next. It complements (does not replace) the per-phase artifacts under this workspace.


<!-- dbmig:section id=inception order=10 -->
## Inception — Assessment & Planning

### Entry path: imported an existing AWS DMS Schema Conversion (DMS SC) project

- Source **MSSQL** → Target **AURORA_POSTGRESQL**
- Project workspace: `migrations/adventureworks-hr-person`
- Schemas imported: PERSON, HUMANRESOURCES

Every converted object was triaged into one of three dispositions:

| Schema | Objects | ACCEPT (keep as-is) | VERIFY (prove) | MANUAL (reconvert) |
|---|---|---|---|---|
| PERSON | 76 | 64 | 8 | 4 |
| HUMANRESOURCES | 50 | 38 | 7 | 5 |
| **All** | **126** | **102** | **15** | **9** |

### What you should be aware of

- **9 object(s) need manual reconversion** (CRITICAL/HIGH action items or explicit "convert manually" instructions). They are marked `needs_human` in the code manifest and must be converted before use:
  - `Person.IX_vStateProvinceCountryRegion`
  - `Person.iuPerson`
  - `Person.IndividualSurveySchemaCollection`
  - `Person.AdditionalContactInfoSchemaCollection`
  - `HumanResources.Employee`
  - `HumanResources.uspUpdateEmployeeLogin`
  - `HumanResources.dEmployee`
  - `HumanResources.uspUpdateEmployeeHireInfo`
  - `HumanResources.HRResumeSchemaCollection`
- **15 object(s) are probabilistic (GenAI/ML) or advisory conversions** kept from DMS SC — they must be proven equivalent and marked verified (see the Validation section).
- **102 object(s) were accepted as-is** (no action items).
- **75 object(s) reported an apply ERROR in DMS SC** (e.g. foreign keys that did not apply to the target). These will be reconciled by `diff-target` and recreated during the load phase — do not assume the target is complete.

### Artifacts

- Triage report per schema: `01-assessment/dms-sc-classification-<SCHEMA>.md`
- Full mapping + classification: `01-assessment/dms-sc-map-<SCHEMA>.json`
- DDL snapshots: `01-assessment/dms-sc/<SCHEMA>/{source,target}/*.sql`
- Code manifest (DMS SC output pre-loaded): `02-construction/code-manifest-<SCHEMA>.yaml`

### Next steps

1. Review the per-schema triage reports.
2. Run `diff-target` to reconcile every object against the **live** target (resolve conflicts). *(Phase 2 — in progress)*
3. Reconvert MANUAL objects with `convert-code` → `apply-schema --code`.
4. Prove VERIFY objects with `gen-tests` / `run-tests`, then record verdicts with `dbmig verify` (tracked in the Validation section).
<!-- /dbmig:section -->

<!-- dbmig:section id=construction order=20 -->
## Construction — Conversion

### Reconciliation against the live target (`diff-target`)
<!-- /dbmig:section -->

<!-- dbmig:section id=construction.humanresources order=21 -->
#### Schema `HUMANRESOURCES`

- MATCH **44**, MISSING **2**, UNMATCHED/system-named **4**, EXTRA **1**.

**2 object(s) MISSING on the target** — DMS SC converted them but they were not applied (commonly foreign keys / triggers). Resolve with `dbmig diff-target --schema HUMANRESOURCES --resolve apply-ours --apply`, or recreate them in the load phase. Examples:

- `HumanResources.dEmployee` (TRIGGER)
- `HumanResources.FK_EmployeeDepartmentHistory_Employee_BusinessEntityID` (CONSTRAINT)

See `01-assessment/dms-sc-diff-HUMANRESOURCES.md` for the full diff.
<!-- /dbmig:section -->

<!-- dbmig:section id=construction.person order=21 -->
#### Schema `PERSON`

- MATCH **61**, MISSING **2**, UNMATCHED/system-named **13**, EXTRA **0**.

**2 object(s) MISSING on the target** — DMS SC converted them but they were not applied (commonly foreign keys / triggers). Resolve with `dbmig diff-target --schema PERSON --resolve apply-ours --apply`, or recreate them in the load phase. Examples:

- `Person.FK_BusinessEntityAddress_BusinessEntity_BusinessEntityID` (CONSTRAINT)
- `Person.FK_BusinessEntityContact_BusinessEntity_BusinessEntityID` (CONSTRAINT)

See `01-assessment/dms-sc-diff-PERSON.md` for the full diff.
<!-- /dbmig:section -->

<!-- dbmig:section id=validation order=30 -->
## Validation & Testing

VERIFY objects (kept from DMS SC but requiring proof — e.g. `5444` ML/GenAI conversions) are tracked here so a verified object is **not re-verified**. Prove equivalence with `gen-tests` / `run-tests`, then record the verdict with `dbmig verify --schema <S> --set verified --objects <names>`.

| Schema | Verified | Pending | Failed | Total |
|---|---|---|---|---|
| HUMANRESOURCES | 0 | 7 | 0 | 7 |
| PERSON | 2 | 6 | 0 | 8 |
| **All** | **2** | **13** | **0** | **15** |

**Still to verify:**

- `HUMANRESOURCES` · `HumanResources.CK_Employee_Gender` (CONSTRAINT) — pending · codes 7795
- `HUMANRESOURCES` · `HumanResources.uspUpdateEmployeePersonalInfo` (PROCEDURE) — pending · codes 7744
- `HUMANRESOURCES` · `HumanResources.vJobCandidateEmployment` (VIEW) — pending · codes 7744
- `HUMANRESOURCES` · `HumanResources.vJobCandidate` (VIEW) — pending · codes 7744,9997
- `HUMANRESOURCES` · `HumanResources.vEmployee` (VIEW) — pending · codes 7795
- `HUMANRESOURCES` · `HumanResources.vJobCandidateEducation` (VIEW) — pending · codes 7744
- `HUMANRESOURCES` · `HumanResources.CK_Employee_MaritalStatus` (CONSTRAINT) — pending · codes 7795
- `PERSON` · `Person.vAdditionalContactInfo` (VIEW) — pending · codes 7744
- `PERSON` · `Person.XMLPATH_Person_Demographics` (INDEX) — pending · codes 7791
- `PERSON` · `Person.XMLPROPERTY_Person_Demographics` (INDEX) — pending · codes 7791
- `PERSON` · `Person.vStateProvinceCountryRegion` (VIEW) — pending · codes 7634,7795
- `PERSON` · `Person.PXML_Person_Demographics` (INDEX) — pending · codes 7791
- `PERSON` · `Person.CK_Person_PersonType` (CONSTRAINT) — pending · codes 7795
<!-- /dbmig:section -->

<!-- dbmig:section id=validation.targetprep order=31 -->
### Target preparation — secondary objects (drop before load / recreate after)

- Schema `PERSON` (target `person`): captured **14** foreign key(s), **8** non-unique index(es), **2** trigger(s) for drop/recreate around the data load. Primary/unique keys are kept.

Scripts: `03-validation/target-prep/PERSON/{drop-preload,restore-postload}-PERSON.sql`. Run `pre-load-drop` before loading data and `post-load-restore` afterwards (dry-run unless `--apply`).
<!-- /dbmig:section -->
