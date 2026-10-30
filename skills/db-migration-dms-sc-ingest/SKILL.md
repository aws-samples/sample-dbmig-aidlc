---
name: db-migration-dms-sc-ingest
description: Alternate Inception/Construction entry for a database migration when the customer has ALREADY run AWS DMS Schema Conversion (DMS SC) and applied the converted schema to the target — but the conversion is not 100% clean (it left action items). Use when the user says things like "I already ran DMS Schema Conversion", "import my DMS SC project", "continue from an existing DMS SC conversion", or points at a local DMS SC project folder. Parses the DMS SC project, classifies every object ACCEPT / VERIFY / MANUAL, reconciles against the live target, and prepares the already-applied target for data load — then rejoins the normal Validation → Operations path. Engine- and schema-generic (Oracle or SQL Server → PostgreSQL or MySQL). Does NOT convert from scratch (that is db-migration-construction).
---

# DMS SC Ingest (import an existing AWS DMS Schema Conversion project)

Use this skill instead of `db-migration-inception` + `db-migration-construction` **when the
customer has already run AWS DMS Schema Conversion**, applied the converted schema to the
target, and wants to *continue* — keeping the DMS SC output where it is clean and only
reworking what the conversion flagged. You still finish through the normal
`db-migration-validation` and `db-migration-operations` phases.

All the deterministic work is done by the `dbmig` toolkit (`./dbmig …`); you (the AI assistant)
review the triage, drive the gates, and perform any MANUAL reconversion via the construction
skill. See `docs/dms-sc-import-design.md`.

## When this applies

- The target already has the DMS-SC-converted schema applied (fully or partially).
- The DMS SC **project folder** is available locally (the tree of `s-*/`, `t-*/`,
  `action-items/`, `apply-result/` files).
- The user wants a like-for-like continuation, not a fresh conversion.

If instead the user wants to convert a schema from scratch, use the standard
`db-migration-orchestrator` path (inception → construction).

## Operating principles

Same as the orchestrator: **phases**, **human gates**, **artifacts + traceability**,
**ambiguity is a hard gate — ask, never assume** (if a disposition, target schema/name,
diff-conflict resolution, or any decision is unclear or could be read more than one way,
STOP and present options + a recommendation, and wait for the user's choice), **safety**
(every target write is gated; dry-run first; never echo
secrets). This skill sits in **Inception + Construction**; Validation and Operations are the
standard skills.

## Step 1 — Intake

Confirm, asking only for what is missing:

1. **DMS SC project directory** — local path to the exported project folder.
   - If the customer only has it in S3, have them copy the project prefix locally first
     (the framework reads the local folder; it does not call the DMS API):
     `aws s3 cp s3://<dms-sc-bucket>/<migration-project-name>/ ./dms-sc-project/ --recursive
     --exclude "*.zip" --exclude "*.pdf"` — then use `--dms-sc-dir ./dms-sc-project`.
2. **Connection file** — `connections.yaml` pointing at the source and the **live target**
   (the one DMS SC applied to). Test it: `./dbmig test-connection --side both`.
3. **Project name** — the `migrations/<project>/` workspace.
4. **Data movement owner** — `framework` (our `migrate-data`, dev/test) or `dms` (an AWS DMS
   task loads data). This decides who owns the load, but the secondary-object drop/restore
   below applies either way.

## Step 2 — Import & classify (Inception)  →  GATE

```bash
./dbmig import-dms-sc --dms-sc-dir <PATH> --project <P>     # loops all schemas
```

Produces per schema: a mapping sidecar (`01-assessment/dms-sc-map-<S>.json`), a triage
report (`01-assessment/dms-sc-classification-<S>.md`), DDL snapshots, and a code manifest
(`02-construction/code-manifest-<S>.yaml`) pre-loaded with the DMS SC output. Every object is
classified:

- **ACCEPT** — no action items → keep the DMS SC conversion as-is.
- **VERIFY** — `5444` ML/GenAI or LOW/MEDIUM advisories → keep, but **prove** it (tracked in
  a verification ledger so it is not re-verified).
- **MANUAL** — CRITICAL/HIGH or an explicit "convert manually" instruction → must be
  reconverted.

**Look up the action-item codes before presenting.** Many DMS SC / SCT action items were
written for older target versions and no longer apply on the current target (for MySQL:
CTEs, window functions, `CHECK`, `LATERAL`, expression defaults are native on 3 / 8.4; some
"supported" items are silent traps, such as `ON DELETE SET DEFAULT`). For the codes in the
triage, read the pair's verified status table and code notes:

| Pair | Action-code reference |
|---|---|
| Oracle → PostgreSQL | `skills/oracle-to-postgresql-playbook/references/tools/sct-action-code-index.md` |
| SQL Server → PostgreSQL | `skills/sqlserver-to-postgresql-playbook/references/tools/sct-action-code-index.md` |
| Oracle → MySQL | `skills/oracle-to-mysql-playbook/references/tools/sct-action-code-index.md` |
| SQL Server → MySQL | `skills/sqlserver-to-mysql-playbook/references/tools/action-code.md` |

Also read the target baseline (`target-baseline-*.md`, see the pair's playbook `SKILL.md`):
DMS SC generates for Aurora MySQL 8.0.32 only, so an Aurora MySQL 8.4 target needs the 8.4
breaks checked. Note in the triage which items the reference marks as obsolete or as traps;
the disposition is still the user's call.

**Present the triage and stop.** Summarize ACCEPT/VERIFY/MANUAL counts and the awareness
items (especially objects DMS SC failed to apply). The `migration-report.md` Inception
section is written for the human. Wait for approval.

## Step 3 — Reconcile against the live target (Construction)  →  GATE

```bash
./dbmig diff-target --schema <S> --project <P>             # report-only first
```

Classifies each object vs. the LIVE target: **MATCH / MISSING / UNMATCHED (system-named) /
EXTRA**. MISSING objects are things DMS SC converted but did not actually apply (commonly
foreign keys). Review `01-assessment/dms-sc-diff-<S>.md`. Resolve conflicts explicitly:

```bash
./dbmig diff-target --schema <S> --project <P> --resolve apply-ours --apply
# or --resolve keep-live / --resolve ask (interactive)
```

Always re-diff against live and let the human choose which version to keep on any conflict.

## Step 4 — Reconvert MANUAL objects (Construction)

For MANUAL-disposition objects, reconvert via the construction skill (seed from the source
DDL; the DMS SC partial output is a hint), then apply:

```bash
./dbmig apply-schema --schema <S> --project <P> --code
```

ACCEPT and VERIFY objects are **not** reconverted.

MANUAL *storage* objects (for example a table whose computed column DMS SC could not
convert, 7708 on a column) are also listed in the code manifest: write the fix as DDL
(usually `ALTER TABLE …`) into the unit's output file, set it `converted`, and apply it
with `--code`. Action items on a **column** count for its table, so such a table triages
MANUAL, not ACCEPT. Re-running `import-dms-sc` keeps any unit whose file you edited or that
was already applied; only untouched DMS SC output is refreshed.

Read DMS SC output that "applied" before trusting it. Seen in practice: a procedure whose
only DML statement was commented out (a silent no-op), a computed column left as a plain,
always-NULL column, and an error logger that referenced an undeclared variable and never
logged. Row counts still match in all three cases; only equivalence tests catch them.

## Step 5 — Prepare the already-applied target for the data load (Validation)  →  GATE

Because the schema already exists, capture and drop the load-hostile secondary objects
(foreign keys, non-unique indexes, triggers), load, then recreate. Primary/unique keys are
kept.

```bash
./dbmig capture-target-objects --schema <S> --project <P>   # read-only; writes scripts
./dbmig pre-load-drop         --schema <S> --project <P> --apply    # before load (gated)
#   … load data: `dbmig migrate-data` (framework) OR your AWS DMS task …
./dbmig post-load-restore     --schema <S> --project <P> --apply    # after load; reconciles
```

Treat `pre-load-drop`/`post-load-restore` as gated: dry-run first (omit `--apply`), confirm,
then apply.

`migrate-data`, `compare` and `reset-identity` load into the DMS SC target schema recorded
by the import (e.g. `adventureworks_person`); pass `--target-schema` to override.

Triggers are dropped for the load, so anything a trigger computes on INSERT is **not**
computed for loaded rows. DMS SC emulates computed columns with triggers (7679). Reconvert
those to `GENERATED ALWAYS AS (…) STORED` columns, or re-run the computation after the load,
and re-run `capture-target-objects` after any change to the target's secondary objects.

## Step 6 — Validate & prove (Validation)  →  GATE

Rejoin the standard flow:

```bash
./dbmig compare    --schema <S> --project <P>        # row reconciliation
./dbmig gen-tests  --schema <S> --project <P>        # Kiro writes equivalence specs
./dbmig run-tests  --schema <S> --project <P>        # same input -> same result
```

Then record VERIFY verdicts so the work is not repeated:

```bash
./dbmig verify --schema <S> --project <P>            # list status
./dbmig verify --schema <S> --project <P> --set verified --objects a,b \
    --by <alias> --method equivalence-test
```

The migration report's Validation section shows verified/pending counts and the outstanding
list.

## Step 7 — Operations

Hand off to `db-migration-operations` for the cutover, rollback, and monitoring plan
(unchanged).

## Traceability

Everything is under `migrations/<project>/`, and `migration-report.md` is the running,
human-readable, phase-aligned summary (Inception → Construction → Validation → Operations)
of what has been done and what to be aware of. Keep it current; it is the backbone a human
reads to understand the migration's state.
