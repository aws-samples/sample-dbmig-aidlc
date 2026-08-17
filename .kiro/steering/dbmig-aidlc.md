---
inclusion: always
---

# dbmig-aidlc — AI-DLC database migration project

This repository is an **AI-DLC-style database migration framework**. When a user asks to
migrate a database or convert a schema in this workspace, follow the framework below rather
than converting ad hoc.

## On a migration request

If the user says anything like "start a database migration", "migrate Oracle to PostgreSQL",
"migrate SQL Server to MySQL", "convert my schema", or "help me move my database", invoke the
**`db-migration-orchestrator`** skill (in `skills/db-migration-orchestrator/`) and let it run
the intake interview and route the phases. Do not skip it or hand-roll the migration.

Supported engine pairs: **Oracle → PostgreSQL**, **Oracle → MySQL**,
**SQL Server → PostgreSQL**, **SQL Server → MySQL**. The active pair is derived from the
connection engines and defined under `engines/<pair>/` with knowledge in
`skills/<pair>-playbook/`.

## Operating principles (AI-DLC)

1. **Phases, not a black box.** Work moves Inception → Construction → Validation → Operations.
   Never skip ahead.
2. **Human gates.** At the end of every phase, present the artifacts and **stop for explicit
   approval** before the next phase. Do not auto-advance.
3. **Artifacts + traceability.** Every phase writes to `migrations/<project>/`. Each converted
   object traces back to the inventory and forward to its apply/test result.
4. **Ambiguity detection.** If a required input is missing or unclear, ask — do not guess.
5. **Safety.** Treat any write to the target (DDL apply, data load, cutover) as a gated action.
   Confirm before destructive operations. Never echo secret values.

## Optional module — application modernization (never auto-starts)

A **separate, optional** module updates *application code* to match a completed database
migration: embedded SQL, datasource/ORM configuration, entity mappings, stored-routine call
sites, error handling and result-set typing.

**Like-for-like only:** the application keeps its architecture, framework and behaviour — only
what the database migration invalidated is changed. This is **not** application refactoring
(no monolith→microservices, framework/language upgrades, ORM swaps, or general cleanup); such
requests are separate engagements outside this module.

**It must never start on its own.** Finishing a database migration is **not** a trigger — at
most, mention that the module exists. Invoke **`app-modernization-orchestrator`** only when the
user explicitly asks to convert, migrate or update *application code*.

When invoked it asks for the **application directory** and the **`migrations/<project>/`
workspace** of the migration to conform to (offering the available candidates if the user does
not know), then runs the same AI-DLC phases with the same gate discipline:
Inception (inventory + **change plan**) → Construction (apply edits) → Validation (build/test)
→ Operations (app cutover). Two rules are absolute: **nothing is edited before the change plan is
approved**, and backups go into a **mirrored `05-application/backup/<timestamp>/` tree — never
`.bak` files beside the originals**.

Per-pair application rules live in `engines/<pair>/app/` (`app-config.yaml`, `app-sql-rules.md`),
so the module extends to new engine pairs without changing any skill.

## Determinism vs. intelligence

The `dbmig` Python package (`scripts/dbmig/`, run as `python -m dbmig <command>`) does all
deterministic work — connect, inventory, extract, apply, copy, reconcile, test — and makes
**no LLM API calls**. The genuinely intelligent step (schema/code conversion and equivalence
test generation) is performed by **you (Kiro)** via the construction/validation skills, using
the pair's datatype map and playbook references as injected context.
