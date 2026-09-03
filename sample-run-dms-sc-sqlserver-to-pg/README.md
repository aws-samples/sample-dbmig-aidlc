# Sample run — continue from an existing AWS DMS Schema Conversion (SQL Server → Aurora PostgreSQL)

This is a complete, real run of the **DMS SC continuation** path, captured end-to-end and
**masked** (no real hosts, usernames, passwords, account ids, or internal resource ids).
It is the companion to [`sample-run-oracle-to-pg/`](../sample-run-oracle-to-pg/): that one
shows a migration converted **purely by dbmig-aidlc** from the source database; **this one
starts from AWS DMS Schema Conversion output** and works forward from there.

- **Source:** SQL Server (`AdventureWorks`, schemas **PERSON** + **HUMANRESOURCES**)
- **Target:** Aurora PostgreSQL — the converted schema was **already applied by DMS SC**
- **Entry skill:** `db-migration-dms-sc-ingest` (reached from the orchestrator's intake)

## The scenario

The customer had already run DMS Schema Conversion (with the GenAI assist) and applied the
converted schema to Aurora PostgreSQL. The conversion is not 100% clean — DMS SC leaves
*action items* on some objects — so instead of re-converting from scratch, the framework
**imports the local DMS SC project, triages every object, reconciles against the live
target, and prepares it for the data load**.

## How this run was produced

```bash
# 0) copy the DMS SC project locally (see the repo README "copy from S3"), then:
python -m dbmig import-dms-sc  --dms-sc-dir /path/to/dms-sc-project --project adventureworks-hr-person
python -m dbmig diff-target    --schema PERSON         --project adventureworks-hr-person
python -m dbmig diff-target    --schema HUMANRESOURCES --project adventureworks-hr-person
python -m dbmig capture-target-objects --schema PERSON         --project adventureworks-hr-person
python -m dbmig capture-target-objects --schema HUMANRESOURCES --project adventureworks-hr-person
# prove the VERIFY (5444 ML/GenAI) objects, then record sign-off so they are not re-verified:
python -m dbmig verify --schema PERSON --project adventureworks-hr-person \
    --set verified --objects <names> --by migration-engineer --method equivalence-test
```

## Triage result (ACCEPT / VERIFY / MANUAL)

`import-dms-sc` classified **126 objects** across the two schemas:

| Schema | Objects | ACCEPT (keep as-is) | VERIFY (prove) | MANUAL (reconvert) |
|---|---|---|---|---|
| PERSON | 76 | 64 | 8 | 4 |
| HUMANRESOURCES | 50 | 38 | 7 | 5 |
| **All** | **126** | **102** | **15** | **9** |

- **ACCEPT** — no action items; the DMS SC conversion is kept unchanged.
- **VERIFY** — `5444` ML/GenAI or LOW/MEDIUM advisories; kept, but proven with equivalence
  tests and tracked in a ledger so they are not re-verified.
- **MANUAL** — CRITICAL/HIGH or an explicit "convert manually" instruction; these are
  reconverted via the construction skill.

## Reconciliation against the live target (`diff-target`)

| Schema | MATCH | MISSING | UNMATCHED (system-named) | EXTRA |
|---|---|---|---|---|
| PERSON | 61 | 2 | 13 | 0 |
| HUMANRESOURCES | 44 | 2 | 4 | 1 |

The **MISSING** objects are ones DMS SC converted but did not actually apply to the target —
here a couple of foreign keys and a trigger (e.g. `HumanResources.dEmployee`). `UNMATCHED`
are PK/UNIQUE/CHECK constraints and indexes DMS SC renamed (a name miss is *not* proof of
absence — they are flagged for a table+columns check, not counted as missing). Full detail
per schema is in `01-assessment/dms-sc-diff-<SCHEMA>.md`.

## Target preparation for the data load (`capture-target-objects`)

Because the schema already exists, the load-hostile secondary objects are captured (so they
can be dropped before a bulk load and recreated after — primary/unique keys are kept):

| Schema | Foreign keys | Non-unique indexes | Triggers |
|---|---|---|---|
| PERSON | 14 | 8 | 2 |
| HUMANRESOURCES | 6 | 5 | 1 |

`drop-preload-<SCHEMA>.sql` and `restore-postload-<SCHEMA>.sql` live under
`03-validation/target-prep/<SCHEMA>/`.

## What's in this folder

```
migration-report.md                      # human-readable, phase-aligned running summary
01-assessment/
  dms-sc-map-<SCHEMA>.json                # full leaf-granular mapping + classification (source of truth)
  dms-sc-classification-<SCHEMA>.md       # the ACCEPT/VERIFY/MANUAL triage report
  dms-sc-verification-<SCHEMA>.yaml        # VERIFY sign-off ledger (2 PERSON objects signed off here)
  dms-sc-diff-<SCHEMA>.md                 # reconciliation vs the live target
  dms-sc/<SCHEMA>/{source,target}/*.sql   # source + DMS-SC-converted DDL snapshots
02-construction/
  code-manifest-<SCHEMA>.yaml             # code objects, pre-loaded with the DMS SC output
  code/<schema>/*.sql                     # the converted routine/view/trigger bodies
03-validation/
  target-prep/<SCHEMA>/capture.json       # captured secondary objects + drop/restore state
  target-prep/<SCHEMA>/{drop-preload,restore-postload}-<SCHEMA>.sql
```

All values here are illustrative and masked; see `sample_connections.yaml` and
`sample_migration-config.yaml` for the (env-var-referenced) configuration shape. For the
design and command reference, see [`docs/dms-sc-import-design.md`](../docs/dms-sc-import-design.md).
