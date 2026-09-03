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

All the deterministic work is done by the `dbmig` toolkit (`python -m dbmig …`); you (Kiro)
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
   (the one DMS SC applied to). Test it: `python -m dbmig test-connection --side both`.
3. **Project name** — the `migrations/<project>/` workspace.
4. **Data movement owner** — `framework` (our `migrate-data`, dev/test) or `dms` (an AWS DMS
   task loads data). This decides who owns the load, but the secondary-object drop/restore
   below applies either way.

## Step 2 — Import & classify (Inception)  →  GATE

```bash
python -m dbmig import-dms-sc --dms-sc-dir <PATH> --project <P>     # loops all schemas
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

**Present the triage and stop.** Summarize ACCEPT/VERIFY/MANUAL counts and the awareness
items (especially objects DMS SC failed to apply). The `migration-report.md` Inception
section is written for the human. Wait for approval.

## Step 3 — Reconcile against the live target (Construction)  →  GATE

```bash
python -m dbmig diff-target --schema <S> --project <P>             # report-only first
```

Classifies each object vs. the LIVE target: **MATCH / MISSING / UNMATCHED (system-named) /
EXTRA**. MISSING objects are things DMS SC converted but did not actually apply (commonly
foreign keys). Review `01-assessment/dms-sc-diff-<S>.md`. Resolve conflicts explicitly:

```bash
python -m dbmig diff-target --schema <S> --project <P> --resolve apply-ours --apply
# or --resolve keep-live / --resolve ask (interactive)
```

Always re-diff against live and let the human choose which version to keep on any conflict.

## Step 4 — Reconvert MANUAL objects (Construction)

For MANUAL-disposition objects, reconvert via the construction skill (seed from the source
DDL; the DMS SC partial output is a hint), then apply:

```bash
python -m dbmig apply-schema --schema <S> --project <P> --code
```

ACCEPT and VERIFY objects are **not** reconverted.

## Step 5 — Prepare the already-applied target for the data load (Validation)  →  GATE

Because the schema already exists, capture and drop the load-hostile secondary objects
(foreign keys, non-unique indexes, triggers), load, then recreate. Primary/unique keys are
kept.

```bash
python -m dbmig capture-target-objects --schema <S> --project <P>   # read-only; writes scripts
python -m dbmig pre-load-drop         --schema <S> --project <P> --apply    # before load (gated)
#   … load data: `dbmig migrate-data` (framework) OR your AWS DMS task …
python -m dbmig post-load-restore     --schema <S> --project <P> --apply    # after load; reconciles
```

Treat `pre-load-drop`/`post-load-restore` as gated: dry-run first (omit `--apply`), confirm,
then apply.

## Step 6 — Validate & prove (Validation)  →  GATE

Rejoin the standard flow:

```bash
python -m dbmig compare    --schema <S> --project <P>        # row reconciliation
python -m dbmig gen-tests  --schema <S> --project <P>        # Kiro writes equivalence specs
python -m dbmig run-tests  --schema <S> --project <P>        # same input -> same result
```

Then record VERIFY verdicts so the work is not repeated:

```bash
python -m dbmig verify --schema <S> --project <P>            # list status
python -m dbmig verify --schema <S> --project <P> --set verified --objects a,b \
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
