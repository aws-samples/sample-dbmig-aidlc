# Migration report — aw-dms-sc-20261030

_Last updated: 2026-10-30 09:39:36Z · maintained automatically by dbmig._

This report is refreshed after each phase. It summarizes what has been done, the current state, and what you should be aware of or do next. It complements (does not replace) the per-phase artifacts under this workspace.


<!-- dbmig:section id=inception order=10 -->
## Inception — Assessment & Planning

### Entry path: imported an existing AWS DMS Schema Conversion (DMS SC) project

- Source **MSSQL** → Target **AURORA_POSTGRESQL**
- Project workspace: `migrations/<project>
- Schemas imported: PERSON, HUMANRESOURCES, DBO

Every converted object was triaged into one of three dispositions:

| Schema | Objects | ACCEPT (keep as-is) | VERIFY (prove) | MANUAL (reconvert) |
|---|---|---|---|---|
| PERSON | 76 | 51 | 20 | 5 |
| HUMANRESOURCES | 50 | 33 | 8 | 9 |
| DBO | 30 | 22 | 2 | 6 |
| **All** | **156** | **106** | **30** | **20** |

### What you should be aware of

- **20 object(s) need manual reconversion** (CRITICAL/HIGH action items or explicit "convert manually" instructions). They are marked `needs_human` in the code manifest and must be converted before use:
  - `Person.vAdditionalContactInfo`
  - `Person.IX_vStateProvinceCountryRegion`
  - `Person.iuPerson`
  - `Person.IndividualSurveySchemaCollection`
  - `Person.AdditionalContactInfoSchemaCollection`
  - `HumanResources.Employee` — reconverted (applied)
  - `HumanResources.uspUpdateEmployeeLogin` — reconverted (applied)
  - `HumanResources.dEmployee` — reconverted (applied)
  - `HumanResources.uspUpdateEmployeePersonalInfo` — reconverted (applied)
  - `HumanResources.vJobCandidateEmployment`
  - `HumanResources.uspUpdateEmployeeHireInfo` — reconverted (applied)
  - `HumanResources.vJobCandidate`
  - `HumanResources.HRResumeSchemaCollection`
  - `HumanResources.vJobCandidateEducation`
  - `dbo.uspSearchCandidateResumes`
  - `dbo.uspGetEmployeeManagers`
  - `dbo.uspGetBillOfMaterials`
  - `dbo.uspGetWhereUsedProductID`
  - `dbo.uspGetManagerEmployees`
  - `dbo.uspLogError` — reconverted (applied)
- **30 object(s) are probabilistic (GenAI/ML) or advisory conversions** kept from DMS SC — they must be proven equivalent and marked verified (see the Validation section).
- **106 object(s) were accepted as-is** (no action items).
- **10 object(s) reported an apply ERROR in DMS SC** (e.g. foreign keys that did not apply to the target). These will be reconciled by `diff-target` and recreated during the load phase — do not assume the target is complete.

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

- MATCH **48**, MISSING **0**, UNMATCHED/system-named **2**, EXTRA **0**.

All mapped objects are present on the target. ✅

See `01-assessment/dms-sc-diff-HUMANRESOURCES.md` for the full diff.
<!-- /dbmig:section -->

<!-- dbmig:section id=construction.person order=21 -->
#### Schema `PERSON`

- MATCH **65**, MISSING **1**, UNMATCHED/system-named **10**, EXTRA **0**.

**1 object(s) MISSING on the target** — DMS SC converted them but they were not applied (commonly foreign keys / triggers). Resolve with `dbmig diff-target --schema PERSON --resolve apply-ours --apply`, or recreate them in the load phase. Examples:

- `Person.FK_StateProvince_SalesTerritory_TerritoryID` (CONSTRAINT)

See `01-assessment/dms-sc-diff-PERSON.md` for the full diff.
<!-- /dbmig:section -->

<!-- dbmig:section id=validation order=30 -->
## Validation & Testing

VERIFY objects (kept from DMS SC but requiring proof — e.g. `5444` ML/GenAI conversions) are tracked here so a verified object is **not re-verified**. Prove equivalence with `gen-tests` / `run-tests`, then record the verdict with `dbmig verify --schema <S> --set verified --objects <names>`.

| Schema | Verified | Pending | Failed | Total |
|---|---|---|---|---|
| DBO | 0 | 2 | 0 | 2 |
| HUMANRESOURCES | 8 | 0 | 0 | 8 |
| PERSON | 15 | 0 | 5 | 20 |
| **All** | **23** | **2** | **5** | **30** |

**Still to verify:**

- `DBO` · `dbo.ErrorLog` (TABLE) — pending · codes 7826
- `DBO` · `dbo.AWBuildVersion` (TABLE) — pending · codes 7826
- `PERSON` · `Person.PXML_Person_AddContact` (INDEX) — failed · codes 7791
- `PERSON` · `Person.XMLVALUE_Person_Demographics` (INDEX) — failed · codes 7791
- `PERSON` · `Person.XMLPATH_Person_Demographics` (INDEX) — failed · codes 7791
- `PERSON` · `Person.XMLPROPERTY_Person_Demographics` (INDEX) — failed · codes 7791
- `PERSON` · `Person.PXML_Person_Demographics` (INDEX) — failed · codes 7791
<!-- /dbmig:section -->

<!-- dbmig:section id=validation.targetprep.humanresources order=31 -->
### Target preparation — `HUMANRESOURCES` (drop secondary objects before load / recreate after)

- Schema `HUMANRESOURCES` (target `adventureworks_humanresources`): captured **6** foreign key(s), **5** non-unique index(es), **1** trigger(s) for drop/recreate around the data load. Primary/unique keys are kept.

Scripts: `03-validation/target-prep/HUMANRESOURCES/{drop-preload,restore-postload}-HUMANRESOURCES.sql`. Run `pre-load-drop` before loading data and `post-load-restore` afterwards (dry-run unless `--apply`).
<!-- /dbmig:section -->

<!-- dbmig:section id=validation.targetprep.person order=31 -->
### Target preparation — `PERSON` (drop secondary objects before load / recreate after)

- Schema `PERSON` (target `adventureworks_person`): captured **13** foreign key(s), **8** non-unique index(es), **2** trigger(s) for drop/recreate around the data load. Primary/unique keys are kept.

Scripts: `03-validation/target-prep/PERSON/{drop-preload,restore-postload}-PERSON.sql`. Run `pre-load-drop` before loading data and `post-load-restore` afterwards (dry-run unless `--apply`).
<!-- /dbmig:section -->
