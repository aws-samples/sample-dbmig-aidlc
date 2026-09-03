# Design — Importing an existing AWS DMS Schema Conversion (DMS SC) project

Status: **accepted / in build** · Owner: dbmig-aidlc · Applies to all engine pairs

## 1. Problem

Today `dbmig-aidlc` converts a schema **from scratch**: inventory the source, let Kiro
convert each object-unit, apply to the target, load data, validate, cut over.

A common real-world situation is different: the customer has **already run AWS DMS
Schema Conversion (DMS SC)** and applied the converted schema to the target — but the
conversion is **not 100% clean**. DMS SC leaves *action items* on some objects:

- **No action item** — DMS SC converted it deterministically. The customer wants to
  **keep the DMS SC output as-is**, not reconvert it.
- **Informational / ML action items** — notably
  `5444 - Severity LOW - This conversion uses machine learning models … should be
  reviewed for accuracy, including human evaluation …`. The code is usable but is a
  **probabilistic (GenAI) conversion that must be verified**.
- **Manual action items** — e.g. `Convert your source code manually.` (typically
  CRITICAL/HIGH). These **must be (re)converted** by us.

After triage we want to re-enter the **normal** dbmig path (data migration →
validation → cutover). Two extra realities must be handled:

1. **The target schema already exists** (DMS SC applied it). Before a bulk data load we
   must **capture, drop, and later recreate** the load-hostile *secondary* objects
   (non-unique/secondary indexes, foreign keys, triggers) — while **keeping primary/
   unique keys** (our `migrate-data` is PK-chunked and resumable and needs them).
2. Data movement may be done by **our toolkit** (`migrate-data`, dev/test) **or by an
   AWS DMS task** (prod, full-load + CDC). The secondary-object capture/drop/recreate
   must work for **both**, and is therefore a **general enhancement**, not something
   specific to the DMS SC import.

## 2. Goals / non-goals

**Goals**
- Ingest a **local DMS SC project folder** and produce dbmig artifacts + a triage that
  classifies every object **ACCEPT / VERIFY / MANUAL**.
- Reuse the existing manifests and downstream commands (`apply-schema`, `migrate-data`,
  `compare`, `gen-tests`, `run-tests`) unchanged.
- Be **engine-pair and multi-schema generic** from day one (Oracle and SQL Server
  sources; PostgreSQL and MySQL targets).
- Always **re-diff against the live target** and let the user resolve conflicts.
- Preserve AI-DLC discipline: phases, artifacts, human gates.

**Non-goals**
- No reconversion of ACCEPT/VERIFY objects (VERIFY is *proven*, not rewritten).
- No new data-movement engine (we keep `migrate-data`; DMS remains the prod option).
- Phase 1 does not touch any database (read-only ingest).

## 3. What a DMS SC project looks like (verified against a real Oracle→Aurora PG export)

A DMS SC project is a flat set of JSON node files plus a few catalogs. Layout:

```
<project>/
  s-server, t-server                     # server_info.vendorName => source/target engine
  s-<sourceId>/  Schemas.DEMO.Tables.BOOKS ...     # SOURCE node tree (one file per node)
  t-<targetId>/  Schemas.demo.Tables.books ...     # TARGET node tree (one file per node)
  action-items/
    ORACLE_TO_AURORA_POSTGRESQL-aid      # action-item CATALOG: code -> {severityType, actionItem, topic, estimatedTime, ...}
    ORACLE-ot                            # object-type catalog: meta-type -> {objectTypeProperty: STORAGE_OBJECT|CODE_OBJECT|SERVER_LEVEL_OBJECT, ...}
    <sourceId>/Schemas.DEMO              # per-schema treeNodeStatistics (messageActions roll-up)
  tree-node-changes/ tnc-*               # apply operations (input)
  apply-result/     ar-*.csv            # what was applied to the target + status
```

**Each node file** is `{"content":[ { … } ]}`. The single element has:
- `type`, `meta-type` (leaf types are singular: `TABLE`, `INDEX`, `CONSTRAINT`,
  `TRIGGER`, `FUNCTION`, `PROCEDURE`, `VIEW`; container/folder types are plural:
  `TABLES`, `INDICES`, `CONSTRAINTS`, `PACKAGES`, `SCHEMAS`, `SERVER` — **skipped**).
- `id` — dotted path, e.g. `Servers.<srv>.Schemas.DEMO.Tables.BOOKS`.
- `locator` — structured coordinates (`schema-name`, `table-name`, `index-name`,
  `constraint-name`, `function-name`, …).
- **`sql`** — the DDL. **Source** node `sql` = original (Oracle/SQL Server) DDL;
  **target** node `sql` = the **DMS-SC-converted** DDL (this is what the customer wants
  to keep where possible).
- `synchronization_object` / `synchronization_objects` — the **cross-link**. On a
  **target** node, `synchronization_object.name` **is the source node id**. On a source
  node, `related_converted_objects` / `synchronization_object` point to the target.
- `children` — category nodes (Constraints / Indexes / Triggers / Partitions).

**Action items appear two ways** (we read both):
1. **Inline** in the target `sql` as comments —
   `/* [5444 - Severity LOW - <message>] */` — and GenAI-authored spans are fenced:
   `/* vvv ---- Beginning of statement generated using GenAI. ---- vvv */ … /* ^^^ … ^^^ */`.
2. **Structurally** — `statistic.messageActions` in the per-schema `action-items/<srv>/Schemas.<S>`
   file, joined to the `-aid` **catalog** (`code -> {severityType, actionItem, …}`).

**Apply results** — `apply-result/ar-*.csv`:
`OperationId,Category,Object,Full Path,Timestamp,Status,Error,Detail,Hint` — the ground
truth of what DMS SC actually pushed to the target and whether it succeeded.

> Parsing conventions are taken from the reference implementation
> `sample-mma-test-manager` (`S3LoaderService.loadFromS3`), which matches source↔target
> by **source id** (uppercased) via `synchronization_object`, keys its object map by node
> id (so **overloaded** routines stay distinct), and skips container meta-types per
> source engine. Its `DatabaseObject` entity separates `*Ddl` (from the SC file),
> `*DdlFromDb` (live database), `*DdlUserOverwrite` (human edit) and `targetDdlConverted`
> (AI) — which directly validates the "always re-diff live vs. SC vs. ours, user chooses"
> design below.

## 4. Classification (ACCEPT / VERIFY / MANUAL)

Per object, gather action items from the inline `sql` markers **and** the structural
`messageActions` (enriched via the `-aid` catalog), plus a `has_genai` flag from the
GenAI fences. Then apply **precedence**:

1. **MANUAL** — any action item whose catalog `actionItem` requires manual work
   (text contains "manual"/"manually"), or a CRITICAL/HIGH item with no automatic
   replacement. → we must (re)convert.
2. **VERIFY** — otherwise, if the object has a GenAI-generated span or any ML/
   probabilistic item (e.g. `5444`, message mentions "machine learning"). → keep the
   DMS SC code, but prove it with equivalence tests.
3. **ACCEPT** — otherwise (no action items). → keep the DMS SC code as-is.

Storage objects (tables/indexes/constraints) are almost always ACCEPT (deterministic).
Code objects (functions/procedures/triggers/views/packages) are where VERIFY and MANUAL
concentrate. Precedence and the manual/verify keyword rules are configurable so the
policy can be tuned without code changes.

## 5. Architecture

Two layers, matching the existing project split (deterministic Python toolkit + Kiro for
intelligence). New work is **additive**.

### 5.1 New parsing module — `scripts/dbmig/dmssc/`
- `model.py` — dataclasses: `DmsScObject`, `ActionItem`, `ImportResult`.
- `parser.py` — vendor/schema-generic reader:
  discover files (`s-*`/`t-*` node dirs, `action-items/`, `*-aid`, `*-ot`, `*-server`,
  `apply-result/*.csv`); detect engines from `*-server`; 3-pass match (source → target →
  action items); expose parsed objects grouped by (schema, category).
- `classify.py` — action-item extraction (inline + structural) + ACCEPT/VERIFY/MANUAL.

### 5.2 New `dbmig` commands (deterministic toolkits)

| Command | Phase | Role | DB effect |
|---|---|---|---|
| `import-dms-sc` | Inception | Parse a local DMS SC dir → manifests + `dms-sc-map` sidecar + classification report; write source/target DDL snapshots. Loops all schemas. | **read-only** |
| `diff-target` | Inception→Construction | Re-diff each object (SC/our DDL vs **live** target) → `MATCH/DIFF/MISSING/EXTRA`; interactive keep/apply on conflict. | read + gated writes |
| `capture-target-objects` | Validation | Introspect live target; snapshot **secondary** objects (secondary indexes, FKs, triggers); emit `drop-preload` + `restore-postload` scripts. Keeps PK/unique. | read + file emit |
| `pre-load-drop` / `post-load-restore` | Validation | Execute drop before load / recreate after (dry-run default, gated). | gated writes |

### 5.3 Reused unchanged
- **MANUAL** → existing construction path (`convert-code` seeds a prompt from the source
  DDL + the DMS SC partial as a hint; Kiro converts; `apply-schema --code` overwrites).
- **ACCEPT / VERIFY** → already `converted` in the manifest with DMS SC DDL as
  `output_file`; VERIFY additionally flows through `gen-tests` / `run-tests`.
- `migrate-data`, `compare` unchanged.

### 5.4 `apply-schema` enhancement (general, Phase 3)
Add a **drop-recreate mode** for when the target schema already exists (DMS SC / DMS
task), alongside today's **defer mode** (greenfield: never create FKs/triggers until
`--post-data`). Both keep PK/unique.

### 5.5 New skill + orchestrator branch (Phase 4)
`db-migration-dms-sc-ingest` documents the ingest+triage; `db-migration-orchestrator`
intake gains a branch: *"Have you already run DMS Schema Conversion?"* → this path
instead of `inventory` / `convert-schema`.

## 6. Artifacts & workspace layout

```
migrations/<project>/
  01-assessment/
    dms-sc-map-<SCHEMA>.json               # full leaf-granular mapping + classification (machine)
    dms-sc-classification-<SCHEMA>.md      # human triage report (ACCEPT/VERIFY/MANUAL)
    dms-sc/<SCHEMA>/source/<id>.sql        # source DDL snapshot (all objects)
    dms-sc/<SCHEMA>/target/<id>.sql        # DMS-SC converted DDL snapshot (all objects)
  02-construction/
    code-manifest-<SCHEMA>.yaml            # code objects (origin: dms_sc), usable by apply/convert/tests
    code/<target_schema>/<base>.sql        # DMS SC converted code (ACCEPT/VERIFY output_file)
    manifest-<SCHEMA>.yaml                 # storage object-units (Phase 3; table-centric for apply/drop-recreate)
```

**Manifest additions** (superset of the native shape; ignored by code that doesn't use
them): `origin: dms_sc`, `disposition: accept|verify|manual`, `source_id`, `target_name`,
`action_items: [{code, severity, message, action, source}]`, `has_genai: bool`,
`dms_apply_status: SUCCESS|ERROR|null`. Status mapping: ACCEPT/VERIFY → `converted`
(VERIFY adds `needs_verification: true`); MANUAL → `needs_human`
(`needs_manual_conversion: true`), with the DMS SC target DDL kept as a reference/hint.

The **sidecar** `dms-sc-map-<SCHEMA>.json` is the leaf-granular source of truth
(keyed on **source node id**) that later phases (`diff-target`, capture/drop/restore)
consume. It also carries the source↔target DDL file references and the parsed apply
results.

## 6a. Verification tracking (VERIFY objects)

VERIFY objects must be *proven* (equivalence tests / human review) — and once proven,
**must not be re-verified**. Verdicts live in a **separate ledger** so they survive a
re-import:

- `01-assessment/dms-sc-verification-<SCHEMA>.yaml`, keyed by **source node id**, one
  entry per VERIFY object: `{object, type, codes, status: pending|verified|failed, method,
  by, at, note}`.
- `import-dms-sc` **seeds** `pending` entries for new VERIFY objects and **preserves**
  existing verdicts on re-import (merge, never overwrite).
- `dbmig verify` lists the ledger and records verdicts:
  `dbmig verify --schema S --set verified --objects a,b --by <alias> --method equivalence-test`.
- The per-schema triage report gains a **Verified** column, and the migration report's
  **Validation** section shows verified/pending/failed counts + the outstanding list.

## 6b. Human-readable migration report (updated every phase)

A single evolving, human-readable report — `migrations/<project>/migration-report.md` —
lets anyone see, at a glance, **what has been done so far** and **what to be aware of /
do next**, without reading manifests or JSON. It is organized by the four dbmig-aidlc
phases (**Inception → Construction → Validation → Operations**); each phase/command
refreshes *its own* section idempotently (delimited by HTML-comment markers, ordered by
phase). `import-dms-sc` writes the **Inception** section (import summary, per-schema
ACCEPT/VERIFY/MANUAL table, awareness items — including DMS SC apply errors — and next
steps) and the **Validation** section (verification progress); `dbmig verify` refreshes
the Validation section. Later phases append Construction and Operations. Implemented in
`dbmig/report.py` (phase constants `INCEPTION/CONSTRUCTION/VALIDATION/OPERATIONS`).

## 7. End-to-end workflow (AI-DLC phases + gates)

```
Inception
  import-dms-sc --dms-sc-dir … --project P        (loops all schemas)
  diff-target                                       → report        [GATE: triage + conflicts]
Construction
  MANUAL:  convert-code (Kiro) → apply-schema --code
  DIFF conflicts: apply chosen version                              [GATE]
  ACCEPT/VERIFY: no reconversion
Validation
  capture-target-objects
  pre-load-drop        (secondary indexes + FKs + triggers; keep PK/unique)  [GATE: destructive]
  migrate-data   OR   hand off to AWS DMS task
  post-load-restore
  compare
  gen-tests / run-tests   (proves ACCEPT + VERIFY)                  [GATE]
Operations   (cutover / rollback / monitoring — unchanged)
```

## 8. Phasing

1. **`import-dms-sc` + classification** — read-only; vendor/schema-generic; emits
   sidecar + classification report + code-manifest + DDL snapshots. Verified against the
   real Oracle sample. *(this change)*
2. **Target introspection + `diff-target`** (PostgreSQL first) — the always-re-diff
   requirement + interactive conflict resolution. **Implemented.** Adds
   `live_schema_catalog` / `routine_definitions` / `view_definitions` to the PG engine
   and a `diff-target` command. Verdicts: **MATCH** (present), **MISSING** (expected but
   absent — reported with the DMS SC apply status), **UNMATCHED** (system-named
   PK/UNIQUE/CHECK constraints and indexes that DMS SC renames — a name miss is *not*
   treated as missing; flagged for a table+columns check), **EXTRA** (present, not in the
   map). Name matching is trusted only for kinds DMS SC preserves (tables, views,
   sequences, triggers, routines, and foreign keys). `--resolve apply-ours|keep-live|ask`
   reconciles MISSING objects; report-only + dry-run by default, `--apply` to execute.
   Verified live against the workshop Aurora target: 16 foreign keys correctly reported
   MISSING (the live schema has 0 FKs — DMS SC failed to apply them), 37 system-named
   objects parked as UNMATCHED, 62 MATCH.
3. **`capture-target-objects` + drop-recreate around the load** — the general
   secondary-object capture/drop/restore (keep PK/unique). **Implemented.** PG engine
   gains `capture_secondary_objects` (FKs, non-unique secondary indexes, triggers — with
   live-captured `create_sql`/`drop_sql`). Commands: `capture-target-objects` (read-only;
   emits `drop-preload` + `restore-postload` scripts and a `capture.json` manifest under
   `03-validation/target-prep/<SCHEMA>/`), `pre-load-drop` and `post-load-restore` (dry-run
   by default, `--apply` to execute; restore reconciles and is resumable via drop/restore
   state in the manifest). Drop order FK→trigger→index; restore order index→trigger→FK.
   Verified live against the workshop Aurora target: a full drop (15 objects) → recreate
   (15) cycle reconciled with the schema returned to its original state. *(A future step
   folds this into `apply-schema` as an explicit drop-recreate mode alongside today's
   defer mode.)*
4. **Orchestrator branch + `db-migration-dms-sc-ingest` skill + guide**, then
   **MySQL / SQL Server parity** and a captured sample run. **Mostly implemented:** the
   ingest skill + orchestrator branch + steering are in. **MySQL target parity is done and
   verified live** — `engines/mysql.py` gained `live_schema_catalog`,
   `routine_definitions`, `view_definitions`, and `capture_secondary_objects` (FKs,
   NON-UNIQUE secondary indexes with FK-backing indexes excluded, triggers with
   schema-qualified names; PK/unique kept), validated against a real Aurora MySQL target
   with a full capture→drop→restore cycle that reconciled. An Oracle→Aurora MySQL DMS SC
   migration project (`dms-sc-migration-project-oracle-mysql`) is **configured** in the
   workshop account; the GenAI conversion is run manually in the DMS SC console, after
   which the exported project is imported via `import-dms-sc` and reconciled with
   `diff-target` against the MySQL target. **SQL Server source is verified end-to-end**
   against two real DMS SC exports (SQL Server → Aurora PostgreSQL): the whole-database
   `AdventureWorks` project (6 schemas — SALES/PURCHASING/PRODUCTION/PERSON/
   HUMANRESOURCES/DBO, 494 objects) and the HR+Person subset (126 objects). The
   engine-generic parser handled the SQL Server `Databases.X.Schemas.Y` hierarchy and the
   `MSSQL_TO_AURORA_POSTGRESQL` catalogs with **no code changes**; `import-dms-sc`,
   `diff-target` (per schema, e.g. PRODUCTION MATCH 136 / MISSING 6) and
   `capture-target-objects` (SALES: 29 FK / 7 index / 4 trigger) all work. Testing these
   heavily multi-schema projects surfaced one fix: `diff-target` now writes a **per-schema**
   Construction subsection to the migration report (`construction.<schema>`) under a shared
   header, so multiple schemas no longer overwrite each other. **SQL Server → Aurora MySQL
   is also verified** against two real DMS SC exports (whole-DB 6 schemas / 494 objects and
   the HR+Person subset) — DMS SC flattens `Database.Schema` into MySQL databases named
   `<db>_<schema>` (e.g. `adventureworks_person`), which the sidecar's `target_schema`
   captures and `diff-target`/`capture-target-objects` use directly (no code changes).
   **All four engine pairs are now validated for the DMS SC continuation path** (Oracle and
   SQL Server → PostgreSQL and MySQL). **Remaining:** a captured
   end-to-end sample run under `sample-run-*`.

## 9. Open questions / decisions

- **Data-movement owner** (resolved): support both. `migrate-data` for dev/test; for a
  DMS task we apply the full schema first and hand over the captured drop/recreate
  scripts. The capture/drop/restore capability applies whether or not data came via DMS
  SC import — it is a general enhancement to the existing pipeline.
- **ACCEPT re-apply policy** (resolved): **always re-diff against the live target** and,
  on conflict, ask the user which version to keep/apply. The apply-result CSV is a hint,
  not proof.
- **VERIFY scope** (resolved): equivalence testing (`gen-tests` / `run-tests`) is
  sufficient; no separate human-checklist deliverable.
- **Multi-schema** (resolved): required. `import-dms-sc` loops every schema in the
  project using the existing schema-scoped manifest/inventory convention.
