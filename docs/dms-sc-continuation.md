# Continue from an existing AWS DMS Schema Conversion (DMS SC) project

Sometimes the customer has **already run AWS DMS Schema Conversion**, applied the converted
schema to the target, and just needs to *continue* — the conversion is rarely 100% clean, so
DMS SC leaves *action items* on some objects. Instead of converting from scratch, point the
framework at the **local DMS SC project folder** and it will import, triage, and continue.

This path is driven by the `db-migration-dms-sc-ingest` skill, reached from the orchestrator's
intake ("Have you already run DMS Schema Conversion?"). It replaces Inception and Construction;
Validation and Operations are the standard ones. It works for all four engine pairs (Oracle or
SQL Server → PostgreSQL or MySQL) and for projects with several schemas.

## Sample prompts

- *"I already ran AWS DMS Schema Conversion and applied it to the target. Import my DMS SC
  project at `./dms-sc-project` and continue."*
- *"Continue from an existing DMS SC conversion — the project folder is at `~/dms/adventureworks`;
  triage it, reconcile against the live target, and prepare it for the data load."*
- *"Import the DMS SC project in `./dms-sc-project`, show me the ACCEPT/VERIFY/MANUAL triage,
  then diff it against the live target."*

## Getting the DMS SC project onto your machine (copy from S3)

DMS Schema Conversion keeps the project files (the `s-*/` source tree, `t-*/` target tree,
`action-items/`, and `apply-result/`) in the **S3 bucket associated with the DMS SC instance
profile**, under a prefix named after your migration project. Copy that prefix to a local
folder (skip the `.zip`/`.pdf` report exports) and point `import-dms-sc` at it:

```bash
# find the bucket + your project prefix
aws s3 ls s3://<your-dms-sc-bucket>/

# copy the project locally (exclude the report exports)
aws s3 cp s3://<your-dms-sc-bucket>/<migration-project-name>/ ./dms-sc-project/ \
  --recursive --exclude "*.zip" --exclude "*.pdf"

./dbmig import-dms-sc --dms-sc-dir ./dms-sc-project --project <P>
```

The framework reads the local folder only — it does not call the DMS API — so you fully
control what is imported. Re-copy after a fresh DMS SC *apply* to refresh `apply-result/`.

What the folder contains:

```
<project>/
  s-server, t-server        # source / target engine
  s-<sourceId>/ ...         # source objects, one JSON file per object (original DDL)
  t-<targetId>/ ...         # target objects (the DMS SC-converted DDL)
  action-items/             # action-item catalog + per-schema statistics
  apply-result/ar-*.csv     # what DMS SC applied to the target, and whether it succeeded
```

## Triage: ACCEPT / VERIFY / MANUAL

`dbmig import-dms-sc` parses the DMS SC project (engine- and schema-generic) and classifies
every object into three dispositions. Action items are read both from the comments DMS SC
writes into the converted SQL (`/* [5444 - Severity LOW - …] */`, and the fenced GenAI spans)
and from its per-schema statistics.

| Disposition | Meaning | What happens |
|---|---|---|
| **ACCEPT** | no action items | keep the DMS SC conversion as-is |
| **VERIFY** | `5444` ML/GenAI or LOW/MEDIUM advisories | keep, but **prove** it (equivalence tests); tracked in a ledger so it is not re-verified |
| **MANUAL** | CRITICAL/HIGH or "convert manually" | reconvert via the construction skill |

Column-level action items count for their table. Any object whose DMS SC **apply failed**
(per `apply-result/`) is also tracked as a construction unit with status `needs_human` and the
DMS SC error, whatever its disposition: it is not on the target and needs a fix.

Storage objects (tables, indexes, constraints) are usually ACCEPT. Code objects (functions,
procedures, triggers, views, packages) are where VERIFY and MANUAL concentrate.

## Commands

Because DMS SC already applied the schema, the toolkit also **reconciles against the live
target** and **prepares it for the data load** (drop load-hostile secondary objects, load,
recreate — keeping primary/unique keys):

```bash
./dbmig import-dms-sc         --dms-sc-dir <PATH> --project <P>   # import + triage (ACCEPT/VERIFY/MANUAL)
./dbmig diff-target           --schema <S> --project <P>         # reconcile vs LIVE target (MATCH/MISSING/UNMATCHED/EXTRA)
./dbmig capture-target-objects --schema <S> --project <P>        # snapshot FKs/indexes/triggers -> drop/restore scripts
./dbmig pre-load-drop         --schema <S> --project <P> --apply # before the data load
#   … load data (dbmig migrate-data, or an AWS DMS task) …
./dbmig post-load-restore     --schema <S> --project <P> --apply # after the data load; reconciles
./dbmig verify                --schema <S> --project <P>         # list/record VERIFY sign-off
```

The workflow, phase by phase:

```
Inception
  import-dms-sc --dms-sc-dir … --project P        (loops all schemas)        [GATE: triage]
Construction
  diff-target → resolve MISSING objects (diff_conflict decision)
  MANUAL / apply-failed: reconvert → apply-schema --code
  ACCEPT / VERIFY: no reconversion                                           [GATE]
Validation
  capture-target-objects
  pre-load-drop        (FKs, secondary indexes, triggers; keep PK/unique)   (destructive: confirm)
  migrate-data   OR   your AWS DMS task
  post-load-restore
  compare
  gen-tests / run-tests   (prove ACCEPT + VERIFY) → verify --set …           [GATE]
Operations   (cutover / rollback / monitoring — the standard phase)          [GATE]
```

### `diff-target` verdicts

| Verdict | Meaning |
|---|---|
| **MATCH** | present on the live target |
| **MISSING** | DMS SC converted it, but it is not on the target (often foreign keys); shown with the DMS SC apply status. A report-only run records a `diff_conflict` decision: `apply-ours`, `keep-live` or `reconvert` |
| **UNMATCHED** | system-named PK/UNIQUE/CHECK constraints or indexes that DMS SC renames; listed for a table + columns check, not counted as missing |
| **EXTRA** | on the target but not in the DMS SC project |

`--resolve apply-ours|keep-live|ask` acts on MISSING objects; it is a dry run unless `--apply`.
Names are truncated to the target's identifier limit (63 bytes on PostgreSQL) before matching.

### Data load around an existing schema

The target already holds the full schema, so a bulk load would fight its foreign keys and
triggers. `capture-target-objects` reads them from the live target and writes
`03-validation/target-prep/<SCHEMA>/drop-preload-<S>.sql` and `restore-postload-<S>.sql`.
`pre-load-drop` runs the drop (FK → trigger → index) and `post-load-restore` recreates them
(index → trigger → FK) and checks every object is back. Primary and unique keys stay in place
(the loader is PK-chunked and resumable). This works whether the data comes from
`./dbmig migrate-data` (dev/test) or an AWS DMS task.

Triggers are dropped for the load, so anything a trigger computes on INSERT is not computed for
loaded rows. DMS SC emulates computed columns with triggers: reconvert those to
`GENERATED ALWAYS AS (…) STORED`, or re-run the computation after the load.

## Proving VERIFY objects

VERIFY verdicts live in a ledger, `01-assessment/dms-sc-verification-<SCHEMA>.yaml`, so they
survive a re-import and are not repeated:

```bash
./dbmig verify --schema <S> --project <P>                         # list status
./dbmig verify --schema <S> --project <P> --set verified --objects a,b \
    --by <alias> --method equivalence-test
```

The validation gate is blocked while VERIFY objects are `pending`; `failed` verdicts need an
explicit acknowledgement (`--ack verify_failed`). The review site's *Decisions* page shows the
ledger.

## Re-importing

Re-run `import-dms-sc` after a new DMS SC conversion or apply. Construction units you edited by
hand, applied, or decided to skip are kept; only untouched DMS SC output is refreshed. When a
project was converted more than once, the newest target node of the same kind wins, and the
latest apply-result row wins.

## Files written

```
migrations/<project>/
  migration-report.md                      # human-readable, phase-aligned summary (refreshed by each command)
  01-assessment/
    dms-sc-map-<SCHEMA>.json               # full mapping + classification (machine-readable)
    dms-sc-classification-<SCHEMA>.md      # triage report (ACCEPT / VERIFY / MANUAL)
    dms-sc-diff-<SCHEMA>.md                # diff-target report
    dms-sc-verification-<SCHEMA>.yaml      # VERIFY ledger
    dms-sc/<SCHEMA>/source|target/*.sql    # source and DMS SC DDL snapshots
  02-construction/
    code-manifest-<SCHEMA>.yaml            # code + MANUAL + apply-failed units (origin: dms_sc)
    code/<target_schema>/*.sql             # DMS SC output (edit here to reconvert)
  03-validation/target-prep/<SCHEMA>/      # captured drop / restore scripts
```

Manifest units carry `origin: dms_sc`, `disposition`, `source_id`, `target_name`,
`action_items`, `has_genai` and `dms_apply_status` (plus `dms_apply_error` when the apply
failed). DMS SC's own target schema names are kept, for example `adventureworks_person`
(SQL Server `Database.Schema` flattened); data commands find them through the mapping file,
or take `--target-schema`.

## Things to expect

DMS SC output that "applied" can still be wrong. Row counts do not catch it; equivalence tests
do. Seen in real runs:

- a computed column became a plain, always-NULL column;
- a procedure whose only DML statement was commented out (a silent no-op);
- an error logger that referenced an undeclared variable and never logged;
- Oracle `NUMBER` parameters became `DOUBLE PRECISION`, so `ROUND(x, 2)` failed at runtime;
- a generated column written with a non-immutable expression failed to apply, taking its
  dependent objects with it.

Look up the action-item codes before presenting the triage: many were written for older target
versions. Each pair's playbook has a verified status table
(`skills/<pair>-playbook/references/tools/sct-action-code-index.md`;
`tools/action-code.md` for SQL Server → MySQL).

See the archived run [`sample-run-dms-sc-sqlserver-to-pg/`](../sample-run-dms-sc-sqlserver-to-pg/)
for every artifact of a real continuation (SQL Server AdventureWorks → Aurora PostgreSQL).
