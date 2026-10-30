# Sample run — continue from an existing AWS DMS Schema Conversion (SQL Server → Aurora PostgreSQL)

This is a complete, real run of the **DMS SC continuation** path, captured end to end and
**masked** (no real hosts, usernames, passwords, account ids, or DMS resource ids).
It is the companion to [`sample-run-sqlserver-to-pg/`](../sample-run-sqlserver-to-pg/):
that one is converted **purely by dbmig-aidlc**; **this one starts from AWS DMS Schema
Conversion output** and works forward from there.

- **Source:** SQL Server 2022 (`AdventureWorks` 2022), schemas **PERSON** + **HUMANRESOURCES**
  (plus **DBO**, which holds the user-defined types they use)
- **Target:** Aurora PostgreSQL 18.6. DMS SC converted and **applied** the schema, as
  `adventureworks_person`, `adventureworks_humanresources` and `adventureworks_dbo`
- **Entry skill:** `db-migration-dms-sc-ingest` (reached from the orchestrator's intake)

## The scenario

The customer ran DMS Schema Conversion and applied the converted schema to Aurora
PostgreSQL. DMS SC leaves *action items* on objects it could not convert cleanly, so instead
of converting again from scratch, the framework imports the local DMS SC project, triages
every object, reconciles against the live target, reconverts what DMS SC got wrong, loads
the data, and proves equivalence.

## How this run was produced

```bash
# DMS SC (console or CLI): assessment, conversion of Person + HumanResources + dbo, apply to
# the target. Then copy the project from the DMS SC S3 bucket (repo README, "copy from S3").
P=aw-dms-sc-20261030
./dbmig import-dms-sc --dms-sc-dir /path/to/dms-sc-project --project $P
for S in PERSON HUMANRESOURCES; do ./dbmig diff-target --schema $S --project $P; done
./dbmig diff-target --schema HUMANRESOURCES --project $P --resolve apply-ours --apply
# MANUAL objects: reconverted by Kiro into 02-construction/code/…, then
./dbmig apply-schema --schema HUMANRESOURCES --project $P --code
./dbmig apply-schema --schema DBO            --project $P --code
for S in PERSON HUMANRESOURCES; do
  ./dbmig capture-target-objects --schema $S --project $P
  ./dbmig pre-load-drop          --schema $S --project $P --apply
  ./dbmig migrate-data           --schema $S --project $P --workers 4   # loads into adventureworks_<schema>
  ./dbmig post-load-restore      --schema $S --project $P --apply
  ./dbmig compare                --schema $S --project $P
  ./dbmig gen-tests              --schema $S --project $P               # Kiro writes the specs
  ./dbmig run-tests              --schema $S --project $P
done
./dbmig verify --schema HUMANRESOURCES --project $P --set verified --objects vEmployee,… \
    --by migration-engineer --method equivalence-test
```

## Triage result (ACCEPT / VERIFY / MANUAL)

`import-dms-sc` classified **156 objects**:

| Schema | Objects | ACCEPT (keep as-is) | VERIFY (prove) | MANUAL (reconvert) |
|---|---|---|---|---|
| PERSON | 76 | 51 | 20 | 5 |
| HUMANRESOURCES | 50 | 33 | 8 | 9 |
| DBO | 30 | 22 | 2 | 6 |
| **All** | **156** | **106** | **30** | **20** |

Most VERIFY items are column-level advisories: 7826 (`DEFAULT getdate()`), 7831
(`newid()` needs uuid-ossp), 7795 (case-sensitive comparisons) and 7791 (index compression).

## Reconciliation against the live target (`diff-target`)

| Schema | MATCH | MISSING | UNMATCHED (system-named) | EXTRA |
|---|---|---|---|---|
| PERSON | 65 | 1 | 10 | 0 |
| HUMANRESOURCES | 48 | 0 | 2 | 0 |

- The HUMANRESOURCES views and `FK_Employee_Person` failed in the DMS SC apply because
  `person.person` did not exist yet; `--resolve apply-ours --apply` created them.
- PERSON's one MISSING object is `FK_StateProvince_SalesTerritory_TerritoryID`, which
  references the Sales schema (not in scope). It is left out on purpose.
- UNMATCHED includes the five XML indexes on `Person.Person`, which DMS SC could not apply
  (btree on `xml`). Details per schema: `01-assessment/dms-sc-diff-<SCHEMA>.md`.

## MANUAL reconversions

Six objects were reconverted; see `02-construction/conversion-log.md`. Three of them looked
fine in DMS SC (applied, no errors) and were wrong:

- **`HumanResources.Employee`**: the computed column `OrganizationLevel` (`GetLevel()`) became
  a plain column, NULL for every loaded row. Now a `GENERATED ALWAYS AS … STORED` column.
- **`uspUpdateEmployeeLogin`**: the UPDATE was commented out, so the procedure did nothing.
- **`dbo.uspLogError`**: referenced an undeclared variable, so no error was ever logged.

Row counts match in all three cases. Only the equivalence tests catch them.

Left open (`needs_human`): the XQuery views (`vJobCandidate*`, `vAdditionalContactInfo`),
the XML DML trigger `iuPerson`, the XML schema collections, and the indexed-view index.

## Data load and validation

| Schema | Rows loaded | Secondary objects dropped / restored | `compare` | `run-tests` |
|---|---|---|---|---|
| PERSON | 141,250 | 23 / 23 | 13/13 tables match | 3/3 |
| HUMANRESOURCES | 934 | 13 / 13 | 6/6 tables match | 16/16 |

VERIFY sign-off: PERSON 15 verified / 5 failed (the XML indexes, not on the target);
HUMANRESOURCES 8 verified. Details: `03-validation/validation-summary.md`.

## Framework bugs this run found (fixed)

- The parser picked a stale target node when the project had been converted twice, or a
  DMS SC-generated helper trigger instead of the table; and an older apply-result file could
  win over the latest one.
- Action items on a **column** were dropped, so `Employee` triaged ACCEPT instead of MANUAL.
- Re-running `import-dms-sc` overwrote hand-reconverted code and reset its status.
- `diff-target` reported names longer than 63 bytes as MISSING (PostgreSQL truncates them)
  and counted trigger functions as EXTRA.
- `apply-schema --code` silently dropped the `CREATE TRIGGER` of a trigger unit.
- `migrate-data` / `compare` wrote to `person` instead of the DMS SC schema
  `adventureworks_person` (now read from the import, or `--target-schema`).
- The loader sent `bit` values as `t`/`f`, which DMS SC's `numeric(1,0)` domain rejects.

## What's in this folder

```
migration-report.md                       # phase-aligned running summary
01-assessment/
  dms-sc-map-<SCHEMA>.json                # leaf-granular mapping + classification
  dms-sc-classification-<SCHEMA>.md       # ACCEPT/VERIFY/MANUAL triage report
  dms-sc-verification-<SCHEMA>.yaml       # VERIFY sign-off ledger
  dms-sc-diff-<SCHEMA>.md                 # reconciliation vs the live target
  dms-sc/<SCHEMA>/{source,target}/*.sql   # source + DMS SC-converted DDL snapshots
02-construction/
  code-manifest-<SCHEMA>.yaml             # code + MANUAL units (DMS SC output pre-loaded)
  code/<target schema>/*.sql              # DMS SC output, or the reconversion for MANUAL units
  conversion-log.md                       # what was reconverted and why
03-validation/
  target-prep/<SCHEMA>/                   # captured secondary objects + drop/restore scripts
  tests/<SCHEMA>/*.test.yaml              # equivalence specs; equivalence-report-<SCHEMA>.*
  reconcile_report-<SCHEMA>.yaml          # compare results; validation-summary.md
data/migrate_report-<SCHEMA>.yaml         # data-load results
```

All values are masked; see `sample_connections.yaml` and `sample_migration-config.yaml` for
the configuration shape. Design and command reference:
[`docs/dms-sc-import-design.md`](../docs/dms-sc-import-design.md).
