# How this framework applies AI-DLC to database migration

`dbmig-aidlc` is a database-migration framework built on the
[AI-Driven Development Life Cycle](https://aws.amazon.com/blogs/devops/ai-driven-development-life-cycle/)
(AI-DLC) — AWS's AI-native methodology where **AI is the central collaborator that plans and
executes, while humans make the critical decisions**. This document explains how the
methodology maps onto a migration; for *what the tool does* and *how to run it*, see the
[README](README.md) and the [per-pair guides](guides/README.md).

## The AI-DLC mental model, applied to a migration

AI-DLC's core loop is: **AI creates a plan → asks clarifying questions to gather context →
implements only after human validation**, repeated for every activity. A database migration
maps onto that loop almost one-to-one:

| AI-DLC step | In a `dbmig-aidlc` migration |
|---|---|
| AI creates a plan | The orchestrator interviews you (engines, connection file, scope), tests connectivity, inventories the source, and proposes a phased migration plan. |
| AI asks for context | Conversion bundles inject the engine datatype map + migration playbook as **context**, and the orchestrator surfaces ambiguous objects (Oracle Text, packages, identity columns) for a decision rather than guessing. |
| Human validates | Nothing advances a phase until you approve its output. Schema/code is **applied to the target only after you accept the conversion**. |
| AI implements | The `dbmig` toolkit applies DDL (FK-aware multi-pass), copies data, reconciles row counts, and runs equivalence tests. |

The two AI-DLC dimensions show up directly:

- **AI-powered execution with human oversight** — Kiro performs the actual schema/code
  conversion and the toolkit does the deterministic heavy lifting (extract, apply, copy,
  reconcile, test), but every irreversible action on the target is a **human gate**.
- **Dynamic collaboration ("Mob")** — the conversion hand-off is a collaborative review:
  Kiro proposes a converted object, you inspect it against the source in the prompt bundle,
  and you approve or send it back. AI-DLC's *Mob Elaboration* becomes the Inception review of
  the inventory and plan; *Mob Construction* becomes the per-object conversion review.

## Phases

AI-DLC defines three phases — **Inception → Construction → Operations** — each producing
richer context for the next. This framework keeps those and **splits out Validation** as an
explicit phase, because in a data migration *correctness of the migrated data and behavior*
is the gate that matters most.

| AI-DLC phase | Framework phase | Skill | What it produces |
|---|---|---|---|
| Inception | Inception — Assessment & Planning | `db-migration-inception` | connectivity check, object inventory, compatibility assessment, migration plan |
| Construction | Construction — Conversion | `db-migration-construction` | converted schema + stored code (LLM-driven; playbook injected as context) |
| (Construction → Operations bridge) | **Validation & Testing** | `db-migration-validation` | test-data load, row-count reconciliation, behavioral **equivalence** tests |
| Operations | Operations & Cutover | `db-migration-operations` | cutover plan, rollback plan, monitoring |

The `db-migration-orchestrator` skill is the entry point that runs the intake interview and
enforces the gate between each phase.

### Sequencing within a phase: defer foreign keys + triggers

Construction and Validation are not just "convert then load" — the *order of operations on the
target* is itself a decision that protects data fidelity. The framework deliberately **defers
foreign keys and triggers to after the data load**:

1. `apply-schema` applies tables, indexes, PK/UK/CHECK and trigger *functions* (pre-data);
2. `migrate-data` loads the data — with **no foreign keys enforcing insert order** and **no
   row triggers rewriting the values being inserted**;
3. `apply-schema --post-data` then adds the foreign keys and `CREATE TRIGGER` bindings.

This is the AI-DLC principle that *accumulated context drives the next step* applied to data
movement: an enforced foreign key would dictate load order, and a value-maintaining trigger
(e.g. one that recomputes a `search_text` column) would fire during `COPY` and diverge the
target from the source. Deferral keeps the migrated data byte-for-byte faithful, then restores
full referential integrity and behavior once the data is in place.

## AI-DLC vocabulary, mapped

AI-DLC deliberately renames Agile rituals to reflect its AI-driven cadence. The equivalents
here:

- **Units of Work** (AI-DLC's replacement for Epics) → **object-units**. The framework
  converts a table *together with* its indexes, constraints (PK/UK/FK/CHECK), triggers,
  comments and grants — a holistic unit — rather than layer-by-layer. PL/SQL packages,
  procedures and functions are each their own unit.
- **Bolts** (AI-DLC's short, intense cycles that replace sprints) → the per-object / per-batch
  convert→review→apply cycles. A unit is extracted, converted, validated, and applied in a
  single short loop; failures are retried automatically (bounded) or escalated to a human.
- **Persistent context across phases** → the per-project workspace under
  `migrations/<project>/` (manifests, prompt bundles, apply/reconcile/equivalence reports).
  Every converted object traces back to the inventory and forward to its apply result and
  test outcome, and the run can be resumed across sessions — exactly the AI-DLC requirement
  that AI "saves and maintains persistent context across all phases … to your project
  repository."

## Quality and traceability

AI-DLC claims quality from *continuous clarification*, *applying organization-specific
standards*, and *comprehensive test suites*, with end-to-end traceability from requirements
to deployment. The framework realizes this as:

- **Standards as injected context** — the active engine pair's datatype map and playbook
  references are fed into every conversion prompt, and **customer-specific knowledge takes
  highest precedence**, so conversions follow *your* conventions, not a generic default.
- **Comprehensive tests** — `gen-tests` samples real source data and has Kiro generate
  behavioral **equivalence** specs (same input → same value / same net effect); `run-tests`
  executes them against both engines inside rolled-back transactions.
- **Traceability** — inventory → manifest entry → prompt bundle → converted DDL → apply
  report → reconciliation → equivalence report, all persisted in the workspace.

## A worked example

[`sample-run-oracle-to-pg/`](sample-run-oracle-to-pg/) is a complete, real run captured
end-to-end — an Oracle `DEMO` schema migrated to Aurora PostgreSQL. It shows each phase's
artifacts, the Kiro conversion hand-off (prompt bundle ↔ converted object), and the final
reports: pre-data schema **14/14 applied** (with foreign keys + the trigger deferred), code
**20/20 applied**, **199 rows** loaded across 14 tables, deferred foreign keys + triggers
**7/7 applied** after the load, data **14/14 reconciled**, and **29/29 equivalence cases
passed**. The run also confirms the fidelity benefit of deferral: `BOOKS.search_text` loaded
**verbatim from the source** because its maintenance trigger was applied only after the data
was in place. It is the most concrete way to see the AI-DLC loop play out on a migration.

## Sample tasks generated per phase (from the captured run)

AI-DLC has the AI **generate a detailed work plan** and execute it as short **bolts**, with a
human **gate** between phases. Below are the actual task lists the agent produced and ran for
the `DEMO` → Aurora PostgreSQL migration, with the real outcomes. Each phase ends at an
explicit approval gate before the next begins.

### Inception — Assessment & Planning
> *AI proposes the plan and the questions; human approves scope before any conversion.*

1. Test connectivity to both engines → **Oracle 19c EE** and **Aurora PostgreSQL 17.7**, both OK.
2. Inventory the `DEMO` schema → **14 tables, 12 sequences, 33 indexes, 1 trigger, 20 PL/SQL
   objects** (5 packages + 5 procedures + 5 functions).
3. Compatibility assessment — surface objects that need a decision rather than a guess:
   - Oracle Text (`CTXSYS.CONTEXT`) full-text index on `BOOKS`;
   - `NUMBER(19,0)` identity columns; `VARCHAR2(n CHAR)`; `NUMBER(1,0)` flag columns; `BLOB`;
   - 5 packages (no PostgreSQL equivalent) and 4 Oracle Text internal `DR$` tables to exclude.
4. Produce the phased migration plan.
> **Gate:** "Approve the inventory and plan?" → approved.

### Construction — Schema conversion
> *Mob Construction: Kiro proposes each converted object-unit; human reviews against the source.*

1. `convert-schema` → extract **14 object-units** into 3 prompt batches.
2. Kiro converts each table object-unit, applying conventions reviewed at the gate:
   `NUMBER(19,0)` identity → `bigint GENERATED BY DEFAULT AS IDENTITY`; `VARCHAR2(n CHAR)` →
   `varchar(n)`; `NUMBER(1,0)` → `smallint` + `CHECK (col IN (0,1))`; `DATE` → `timestamp(0)`;
   `BLOB` → `bytea`; Oracle Text index → PostgreSQL **GIN `to_tsvector`** + a maintenance trigger.
3. `apply-schema` (pre-data) → **14/14 applied** — tables, 28 indexes, 41 CHECK constraints;
   **foreign keys and triggers deferred** (verified target had 0 FKs / 0 triggers afterward).
> **Gate:** "Approve the converted schema before applying?" → approved (dry-run first).

### Construction — Code conversion
> *One bolt per code object; automatic checks run before the hand-off.*

1. `convert-code` → **20 code objects** (5 packages, 5 procedures, 5 functions).
2. **Naming-conflict check** on the `<package>_<subprogram>` flattening → **clean** (17 package
   subprograms + 10 standalone routines, no collisions).
3. Kiro converts each object: packages flattened to `demo.<package>_<subprogram>` routines;
   PL/SQL → PL/pgSQL (`NVL`→`coalesce`, `SYSDATE`→`now()`, `REGEXP_LIKE`→`~`, PIPELINED →
   `RETURNS TABLE`, `RAISE_APPLICATION_ERROR`→`RAISE EXCEPTION`, cross-calls rewritten).
4. `apply-schema --code` → **20/20 applied**.
> **Gate:** "Approve the converted code?" → approved.

### Validation & Testing
> *Correctness gates: data fidelity, then behavioral equivalence.*

1. `migrate-data` → **199 rows across 14 tables**, loaded in FK-dependency tiers (no manual
   ordering); identity sequences reset to `MAX(id)` after load.
2. `apply-schema --post-data` → apply the deferred **16 foreign keys + trigger** now that data
   is in place. Confirmed `BOOKS.search_text` is **verbatim from source** (trigger deferred).
3. `compare` → **14/14 tables reconcile** on row counts.
4. `gen-tests` → sample real rows for **15 callables**; Kiro writes **9 `.test.yaml`**
   equivalence specs from the sampled data.
5. `run-tests` → **29/29 cases pass** (6 skipped: a set-returning table function and 5 mutating
   procedures that `COMMIT`, which the rolled-back harness can't isolate — flagged, not hidden).
> **Gate:** "Approve the equivalence results?" → approved, with the 6 skips noted as follow-up.

### Operations & Cutover
> *Applies the accumulated context; not exercised in the captured dev/test run.*

1. Produce cutover plan (for production volumes, hand off bulk movement to **AWS DMS**).
2. Produce rollback plan and monitoring checklist.
> **Gate:** "Approve cutover?" — the captured run stops here (dev/test scope).

Every task above left a **persistent artifact** in the workspace (manifest entry, prompt
bundle, converted file, apply/reconcile/equivalence report), so any item traces back to the
inventory and forward to its result — the AI-DLC traceability requirement, realized.
