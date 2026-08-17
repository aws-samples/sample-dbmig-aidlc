---
name: app-modernization-orchestrator
description: >
  OPTIONAL module — entry point for modernizing APPLICATION CODE to match a completed
  database migration. Use ONLY when the user explicitly asks to migrate, convert or
  update an application (its embedded SQL, datasource config, ORM mappings, stored-routine
  call sites and error handling) after a schema migration. Engine-agnostic across all
  supported pairs (Oracle or SQL Server → PostgreSQL or MySQL): the pair's app-layer rules
  are read from engines/<pair>/app/. Follows the same AI-DLC phases as the database migration
  — Inception (inventory + change plan) → Construction (apply edits) → Validation (build/test)
  → Operations (cutover) — with a human gate at every phase. NEVER starts automatically, and
  NEVER edits an application file before the change plan is approved. Does not convert schema
  or in-database stored code — that is db-migration-construction.
---

# Application Modernization — Orchestrator (optional module)

This module updates an **application** so it works against a migrated database. It is a
companion to the database migration, and it deliberately uses the **same AI-DLC phases and gate
discipline** as the migration itself, so there is one vocabulary across the framework.

## Scope: like-for-like only

This is **like-for-like modernization**: the application keeps its architecture, framework,
language and behaviour — only what the database migration invalidated is changed (embedded SQL
dialect, datasource/ORM configuration, routine call sites, error codes, result-set typing).

It is **not application refactoring**. Out of scope, even if asked mid-run: breaking a monolith
into microservices, framework or language upgrades, ORM swaps (e.g. JDBC → JPA), architectural
restructuring, performance rewrites, or general code cleanup. If the user wants any of those,
treat it as a separate engagement — finish (or pause) this module first, so the like-for-like
diff stays reviewable and attributable to the database change alone.

## Two hard rules

1. **Never auto-start.** This module runs only when the user explicitly asks to convert,
   migrate or update *application code*. Completing a database migration is **not** a trigger —
   at most, mention that this module exists.
2. **Never edit before approval.** The Inception gate presents a **change plan** (the change
   summary) and must be approved before the first application file is modified.

## Phases (mirroring the database migration)

| # | AI-DLC phase | Skill | Output | Gate question |
|---|---|---|---|---|
| 1 | **Inception** — assessment & planning | `app-modernization-inception` (+ this skill for the plan) | app contract, inventory, **change plan** | "Approve the application assessment & change plan?" |
| 2 | **Construction** — conversion | `app-modernization-construction` | edited files + mirrored backups, conversion log | "Approve the converted application?" |
| 3 | **Validation & Testing** | `app-modernization-validation` | build/test results, fixes, verification matrix | "Approve the application validation results?" |
| 4 | **Operations & Cutover** | `app-modernization-operations` | app cutover/rollback notes feeding the DB runbook | "Approve the application cutover plan?" |

The skill names mirror the database module (`db-migration-inception` … `db-migration-operations`)
one-for-one, so the whole framework speaks a single phase vocabulary.

Same operating principles as the database migration: phases not a black box, a human gate at the
end of each, artifacts for traceability, ask rather than guess, and treat writes as gated.

## Artifacts

The app module lives **inside the database migration's workspace** and mirrors its phase folders
one level down, so an app change is always traceable to the schema change that caused it:

```
migrations/<project>/05-application/
├── 00-intake/app-intake.md        # app dir, stack, engine pair, scope, git state
├── 01-assessment/
│   ├── app-contract.md            # DB change -> required app change (derived, cited)
│   ├── inventory.md               # every impacted site, classified
│   └── change-plan.md             # THE CHANGE SUMMARY presented at the Inception gate
├── 02-construction/
│   └── conversion-log.md          # what changed, with rationale
├── 03-validation/
│   └── build-report.md            # build, fixes, tests, verification matrix
├── 04-operations/
│   └── app-cutover.md             # deploy/rollback steps, cross-referenced to the DB runbook
└── backup/<YYYYMMDD-HHMMSS>/      # mirrored originals (see Backup policy)
```

`backup/` sits at the module root rather than under `02-construction/` on purpose: originals need
to be easy to find, list and diff long after the run.

## Step 0 — TODO list

Create a task list with the four phases and their gates, plus intake.

## Phase 0 — Intake (ask only for what is missing)

1. **Application directory** — absolute path. Required; never guess.
2. **Database-migration project folder** — the `migrations/<project>/` workspace of the completed
   migration. If the user does not know it:
   - list candidates (`ls migrations/`), showing each one's schema and engine pair from
     `00-intake/intake.md`, and ask which applies;
   - if none exists, say so plainly: without it the module can only apply generic dialect rules
     and cannot know what *this* migration did. Offer "generic mode" with that limitation
     recorded, or stop.
3. **Engine pair** — derive from the migration workspace (or `connections.yaml`). Confirm
   `engines/<pair>/app/` exists; if not, the pair is not yet supported here — stop and say so.
4. **Application stack** — detect, then confirm:
   - `pom.xml` / `build.gradle` → Java (Spring Boot? JPA/Hibernate? MyBatis? plain JDBC?)
   - `*.csproj` / `*.sln` → .NET (EF Core, Dapper, ADO.NET)
   - `requirements.txt` / `pyproject.toml` → Python (SQLAlchemy, psycopg/oracledb)
   - `package.json` → Node.js (Sequelize, TypeORM, Knex, raw driver)
   Record the build and test commands to be used in Validation.
5. **Scope** — in-scope directories, and confirm exclusions. Build output (`target/`, `bin/`,
   `obj/`, `dist/`, `out/`) and vendored dependencies are **always** excluded.
6. **Git state** — if the app is a git repo, run `git status`. A dirty tree makes review hard;
   recommend committing or stashing first. Record the current commit.
7. **Source-dialect state** — confirm the application still speaks the SOURCE dialect. If it was
   already converted for a different target (e.g. a PostgreSQL run preceding a MySQL one), do
   **not** convert the converted app: restore an original-state copy from that run's mirrored
   backup (`cp -R` the app, then copy the backup tree over it) and convert the copy. Converting a
   converted app compounds two dialect translations and breaks traceability to the source.

Write `00-intake/app-intake.md`. Stop if the app directory or a usable migration workspace cannot
be established.

## Phase 1 — Inception (assessment & planning)

### 1a. Build the app contract — before inventory

Do **not** start from generic dialect rules. Start from what this migration actually did:

| Read | Extract |
|---|---|
| `00-intake/intake.md` | engine pair, source schema → target schema/database |
| `02-construction/conversion-log.md` | identifier folding, datatype choices, renamed/flattened routines, error-code mapping, removed `COMMIT`s, redesigns such as full-text |
| `02-construction/code-manifest-*.yaml` | the actual converted routine names |
| `03-validation/validation-summary.md` | the **"carry-forward for the application team"** list — the app's to-do list, already written |
| `engines/<pair>/app/app-config.yaml` | driver, URL, dialect, error style, identity handling |
| `engines/<pair>/app/app-sql-rules.md` | dialect + behavioural SQL rules |

Write `01-assessment/app-contract.md`: a table of **DB change → required app change**, each row
citing its source. Where the validation summary already lists carry-forward items, they are
authoritative — reproduce them, do not re-derive them.

This is what makes the module accurate rather than generic: the app is conformed to *this*
migration, not to a dialect pair in the abstract.

### 1b. Inventory

Invoke **`app-modernization-inception`** → `01-assessment/inventory.md`.

### 1c. Change plan — and the gate

Write `01-assessment/change-plan.md` containing:

1. **Scope** — files to change, counts by category, and what is excluded.
2. **Per-site preview**, ordered by risk:

   ```
   ### <n>. <relative/path>:<line>   [mechanical | BEHAVIOURAL | blocked]
   Current:   <exact current code>
   Proposed:  <exact proposed code>
   Why:       <the DB migration decision that requires it, cited>
   Risk:      <what breaks if wrong; "none — syntax only" is a valid answer>
   ```
3. **Behavioural changes first and separate** — anything that can alter results silently
   (`ROWNUM`+`ORDER BY`, NULL/empty string, format masks, search ranking, count types).
4. **Blocked / needs-a-decision** items with options, not a guess.
5. **Backup location** to be used.
6. **Verification plan** — the exact build and test commands.
7. An explicit statement that **nothing has been edited yet**.

Then **stop: "Approve the application assessment & change plan?"** Approval may be partial —
record deferred items and skip them. For a large change set keep the *presented* summary readable:
group mechanical changes by rule with counts and file lists, enumerate behavioural ones
individually, and leave full detail in the file.

## Phase 2 — Construction (conversion)

Only after approval, invoke **`app-modernization-construction`**.

### Backup policy (mandatory)

**Never create `.bak` files beside the originals.** They clutter the source tree, get picked up by
builds and packaging, and are easy to commit by accident.

Back up into a **mirrored tree**:

```
migrations/<project>/05-application/backup/<YYYYMMDD-HHMMSS>/<path relative to app root>
```

e.g. `src/main/resources/application.properties` →
`…/backup/20260817-153000/src/main/resources/application.properties`

- One timestamped directory per run; never overwrite a previous run.
- Copy a file immediately before its first edit, preserving the relative path and mode (`cp -p`).
- Back up only files actually edited; write `MANIFEST.md` listing each with size and reason.
- Never place a backup inside the application directory or inside build output.

Restore is one mirrored copy back, and `diff -r` compares the whole tree at once.

Gate: **"Approve the converted application?"** — present the diff summary and the conversion log.

## Phase 3 — Validation & Testing

Invoke **`app-modernization-validation`**: compile, fix migration-caused failures, run tests, and record
a per-site verification matrix. Compile errors from the migration (types, error codes, driver APIs)
are expected, and fixing them is part of this module.

Gate: **"Approve the application validation results?"** Be explicit about what is `UNVERIFIED`.

## Phase 4 — Operations & Cutover

Invoke **`app-modernization-operations`**: the application and the database must cut over
**together**, and the DB cutover runbook already treats the converted app build as a
precondition (its step 0.1). The skill produces `04-operations/app-cutover.md` — deploy
artifact + configuration (secrets by reference), ordering against the DB runbook, rollback,
post-cutover checks that exercise the *converted* code paths, and the open behavioural risks
with owners.

Gate: **"Approve the application cutover plan?"**

## Safety

- Application source is user code: **editing it is a gated action**, gated at the Inception gate.
- Never edit build output. If a stray `.bak`/`.orig` is found there (a common leftover from ad-hoc
  conversions), report it rather than "fixing" it.
- Never commit on the user's behalf unless asked.
- Datasource files often hold **plaintext credentials**. Never echo secret values; show structure
  with the secret redacted and recommend environment variables or a secrets manager.
- If the target database is reachable, prefer validating identifiers against the live catalog over
  inferring them — read-only. This module never writes to a database.
