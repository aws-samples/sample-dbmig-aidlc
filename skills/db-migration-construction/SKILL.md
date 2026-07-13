---
name: db-migration-construction
description: Construction phase (conversion) of an AI-DLC database migration. Use after the Inception migration plan is approved, or when the user asks to convert/translate a source database schema, tables, datatypes, views, or stored code (PL/SQL, T-SQL, etc.) to the target engine. Engine-agnostic across all supported pairs (Oracle or SQL Server → PostgreSQL or MySQL). The conversion is LLM-driven and YOU (Kiro) are the LLM: the dbmig Python tool extracts source object-units and writes prompt bundles, you convert each bundle to target DDL using the active pair's playbook references as context, then dbmig applies the DDL to the target. Writes artifacts to migrations/<project>/02-construction/.
---

# Construction — Conversion (LLM-driven; you are the LLM)

This is the **Construction** phase. Conversion is **not rule-based** — the `dbmig`
Python package does the deterministic work (extract object-units, write prompt bundles,
apply DDL, report errors), and **you (Kiro) perform the actual source→target conversion**
using the active pair's playbook references as your knowledge base.

The package never calls a hosted LLM. It runs with `provider: kiro` (hand-off mode).

## Active engine pair (read this first)

The framework supports multiple pairs. Determine the **active pair** from the connection
engines in `connections.yaml`: `<source>-to-<target>` (e.g. `oracle-to-postgresql`,
`oracle-to-mysql`, `sqlserver-to-postgresql`, `sqlserver-to-mysql`). Throughout this skill,
substitute that pair for `<pair>`:

- Knowledge base / playbook references: `skills/<pair>-playbook/references/...`
- Engine definition + datatype map: `engines/<pair>/`

The prompt bundles `dbmig` writes already inject the **correct** pair's context, so you
mostly read the bundle; open the pair's playbook topic files when you need more detail.

## The conversion loop

### 1. Prepare (dbmig extracts + builds prompts)
```bash
python -m dbmig convert-schema --schema <SCHEMA> --project <project>
# or a subset:
python -m dbmig convert-schema --schema <SCHEMA> --tables ORDERS,CUSTOMERS --project <project>
```
This extracts each **object-unit** (one table + its indexes + constraints (PK/UK/CHECK)
+ foreign keys + DML triggers + comments/grants), batches small tables together, and
writes:
- prompt bundles → `migrations/<project>/02-construction/prompts/<SCHEMA>/*.prompt.md`
- a manifest → `migrations/<project>/02-construction/manifest-<SCHEMA>.yaml` (one row per
  unit: `name, batch_id, prompt_file, output_file, status: pending`). Manifests are
  **schema-scoped**, so one `--project` can hold several schemas (migrate referenced schemas
  first so cross-schema foreign keys resolve at `--post-data`). Older single-schema runs with
  a plain `manifest.yaml` are still read as a fallback.

### 2. Convert (YOU do this — the core LLM step)
For each `pending` unit in the manifest:
1. Read its prompt bundle. It already injects the construction guidance, the active pair's
   datatype map, and the pair's playbook topic index. Open the specific
   `skills/<pair>-playbook/references/...` topic files the unit needs (datatypes,
   constraints, triggers, sequences/identity, indexes, etc.).
2. Convert the whole object-unit **holistically** to the **target** engine's DDL — choose
   the right types, index kinds, and constraint forms given the full unit; fold identifier
   case per the target's convention; and rewrite **source-specific constructs** flagged in
   the pair's playbook (e.g. Oracle `ROWNUM`/`DUAL`/`NVL`, SQL Server `TOP`/`IDENTITY`/
   `GETDATE()`/`ISNULL`). A batch prompt converts several tables — write each table's DDL
   to its own output file.
   - **Customer-specific knowledge wins.** Apply any rules under
     `skills/<pair>-playbook/references/customer-specific/` first — they OVERRIDE the general
     playbook (and the datatype map) on conflict. The prompt bundle already injects them at
     the top, labeled highest precedence.
3. **Write the target DDL** to the unit's `output_file`
   (`02-construction/ddl/<schema>/<table>.sql`). Return only SQL (fenced or plain).
4. Set that unit's `status` to `converted` in `manifest.yaml`.
5. Record notable decisions / risky constructs as SQL comments and in a short
   `02-construction/conversion-log.md`, citing the playbook reference used (traceability).

### 3. Apply (dbmig applies to the target — gated)
```bash
python -m dbmig apply-schema --schema <SCHEMA> --project <project>
```
- Applying DDL writes to the target — a **gated action**. Confirm before the first run.
- `apply-schema` is **status-aware**: it skips units already `applied` (so re-running after
  a fix never re-triggers "already exists"), and applies multi-pass so foreign keys to
  not-yet-created tables resolve on a later pass.
- **Foreign keys + triggers are deferred.** The default `apply-schema` applies tables,
  indexes, PK/UK/CHECK and trigger *functions*, but holds back `FOREIGN KEY` constraints and
  `CREATE TRIGGER` statements. Those are applied later by `apply-schema --post-data`, **after**
  `migrate-data` (Validation phase) — so enforced FKs don't dictate load order and row triggers
  don't rewrite the data being loaded. The deferred pass is tracked in a separate `post_status`
  field (independently idempotent).
- It writes `02-construction/apply_report.yaml` and updates each unit's status/attempts in
  the manifest. Use `--dry-run` to preview the DDL without executing it.

**Automated error-retry loop (minimize human-in-the-loop).** When a unit fails to apply,
`apply-schema` captures the **target database error** and writes a **remediation prompt** at
`02-construction/retries/<SCHEMA>/<unit>.retry.md` (original prompt + the failed DDL + the
exact error), enforcing `llm.max_retries` (default 3) per unit. Follow this loop:

1. Run `apply-schema`.
2. If the output contains **`RETRY_AVAILABLE`**: for each listed failed unit, read its
   `retries/<SCHEMA>/<unit>.retry.md`, produce **corrected** target DDL, overwrite the
   unit's `output_file`, then run `apply-schema` again. Repeat automatically.
3. Stop when apply reports **all units applied** (success) or **`MAX_RETRIES_EXHAUSTED`**
   (units that hit `max_retries` are marked `needs_human`).
4. Only on `MAX_RETRIES_EXHAUSTED` bring the human in: summarize the `needs_human` units and
   their `last_error`, and propose options (redesign, a `customer-specific/` override, or
   skipping the object).

Override the cap with `--max-retries N`, or target units with `--tables ORDERS,CUSTOMERS`.
Use `--code` to run the same loop for code objects.

### 4. Code objects (separate pass)
Stored code (packages, procedures, functions, types — PL/SQL or T-SQL depending on the
source) needs different context and often iterative refinement:
```bash
python -m dbmig convert-code --schema <SCHEMA> --project <project>   # writes code_prompts/ + code-manifest.yaml
# you convert each code object -> 02-construction/code/<schema>/*.sql, set status converted
python -m dbmig apply-schema --schema <SCHEMA> --project <project> --code
```
Constructs with no direct target equivalent (e.g. Oracle packages, SQL Server CLR/Service
Broker) are redesigned per the pair's playbook (see its `sql-plsql/` or `tsql/` references).
Expect convert → apply → test → refine cycles.

**Package-flattening naming conflicts (Oracle).** Packages are flattened to
`<package>_<subprogram>` routines. `convert-code` automatically checks (via `ALL_PROCEDURES`)
whether that underscore-join is unique and **warns + records `naming_conflict` items to
`follow-up.yaml`** when two different Oracle routines collapse onto the same name (e.g.
`BOOK_PKG.GET_X` and `BOOK.PKG_GET_X` both → `book_pkg_get_x`, or a package routine shadowing
a standalone). Resolve flagged collisions by using a distinct separator (e.g. the AWS SCT
`<package>$<subprogram>` style) or an explicit rename — see the pair's
`checks/package-naming.md`.

## Holistic, object-unit conversion (why)
Converting a table with its indexes, constraints, and triggers together lets you make
decisions a layer-by-layer pass cannot — e.g. picking an index type informed by a
constraint, or folding a simple trigger into a `CHECK`/`GENERATED` column. Always convert
the unit as a whole.

## Handling hard cases
- For Manual/Blocked items from Inception, propose the redesign, explain the tradeoff,
  get the user's decision, then implement. Don't silently approximate behavior — the
  Validation phase will test for equivalence and surface it.
- Leave clearly-commented TODOs for anything that needs human review.

## Gate
When the planned units are converted and applied, summarize: units converted/applied by
status (from the manifest + apply report), anything deferred/blocked, and where the DDL
lives. **Stop at the gate: "Approve the converted schema + code?"** Then hand off to
`db-migration-validation`.
