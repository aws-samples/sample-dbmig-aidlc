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
end of each, artifacts for traceability, and treat writes as gated. **Ambiguity is a hard gate —
ask, never assume:** if the target framework/dialect, a datasource/config value, an error-code
mapping, which migration workspace to conform to, or any edit decision is unclear or has more
than one reasonable interpretation, STOP and present the options with a recommendation and wait
for the user's choice rather than guessing (a wrong assumption that diverges from the customer's
requirement is worse than a question).

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

**Optional application questionnaire.** Some teams prefer to answer up front, often because the
application owner is not the person running the database migration. Mention it once, in one
sentence, and continue without waiting: *"If you prefer, I can generate a questionnaire your
application team fills in (`./dbmig questionnaire new --module app --project <P>`); otherwise
I'll ask as we go."* When the user wants it, or an answered
`05-application/00-intake/app-questionnaire.md` already exists:
1. `./dbmig questionnaire check --module app --project <P>` lists missing / invalid answers and
   free-text "Other" answers. Clarify "Other" answers with the user.
2. `./dbmig questionnaire check --module app --project <P> --apply` records the answers in
   `project.yaml` (`app.intake`, `app.policies`) and writes
   `05-application/00-intake/app-policies.md`. **Read that file before the change plan and before
   every edit: its policies take precedence over the general app-layer rules**, and cite the
   policy key in the conversion log where you apply one.
3. Ask only the intake items below that the questionnaire did not answer. A questionnaire never
   approves a gate.

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
6. **Git state and backup mode** — if the app is a git repo, run `git status`. **When the app is in
   git, git is the backup by default** (`backup_mode: auto`, or `git` if the customer asks). Git can
   be used only with a clean in-scope working tree: recommend committing or stashing first. Ask
   which to use only if the customer has a preference: `auto` (git when possible, else a file
   copy, recommended), `git`, or `file-copy`. Ask where edits go in git: left **uncommitted** in
   the working tree (recommended; never commit or push), or on a new local branch
   `dbmig/<project>`. **If it is NOT a git repo, say so loudly** in the intake summary: *the
   mirrored file copy is the only rollback.* Record the choice in `app-intake.md`; the backup
   itself is made by `./dbmig app-backup` at the start of Construction (see Backup policy), which
   falls back to a file copy whenever git cannot be used, so no file is edited without a backup.
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
| `engines/<pair>/app/customer-specific/*.md` | **highest precedence** — the customer's own app conventions, datasource config, error-code mappings, forbidden patterns (overrides the generic rules above) |

Write `01-assessment/app-contract.md`: a table of **DB change → required app change**, each row
citing its source. Where the validation summary already lists carry-forward items, they are
authoritative — reproduce them, do not re-derive them.

This is what makes the module accurate rather than generic: the app is conformed to *this*
migration, not to a dialect pair in the abstract.

### 1b. Inventory

Invoke **`app-modernization-inception`** → `01-assessment/inventory.md`. It starts with the
deterministic `./dbmig app-scan --app-dir <APP_DIR> --project <project>` pre-scan (one pass over
the whole tree, entity↔target type cross-check) and then reads only the flagged files — required
for large code bases, where reading every file is not affordable.

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
5. **Backup** to be used: mode (`auto` / `git` / `file-copy`), in-scope paths, and where edits go
   in git (uncommitted, or branch `dbmig/<project>`).
6. **Verification plan** — the exact build and test commands.
7. An explicit statement that **nothing has been edited yet**.

Then **stop: "Approve the application assessment & change plan?"** and record the gate (see
*Gates are recorded* below) as `app-inception`. Approval may be partial —
record deferred items and skip them. For a large change set keep the *presented* summary readable:
group mechanical changes by rule with counts and file lists, enumerate behavioural ones
individually, and leave full detail in the file.

## Phase 2 — Construction (conversion)

Only after approval, invoke **`app-modernization-construction`**.

### Backup policy (mandatory)

**Never create `.bak` files beside the originals.** They clutter the source tree, get picked up by
builds and packaging, and are easy to commit by accident.

Make the backup with one command, **before the first edit**:

```bash
./dbmig app-backup --project <P> --app <APP_DIR> [--mode auto|git|file-copy] [--scope src,pom.xml]
```

- `auto` (default) uses **git** when the app is in a git repository with a commit and no
  uncommitted in-scope changes: it records the base commit, and copies only the in-scope files
  git ignores (local config, for example), because git cannot restore those. Otherwise it makes a
  **file copy** of the whole in-scope tree into
  `migrations/<project>/05-application/backup/<YYYYMMDD-HHMMSS>/` (mirrored paths, timestamps and
  modes kept; build output and dependencies excluded).
- `git` falls back to a file copy when git cannot be used (not a repo, no commit, uncommitted
  changes, git not installed), and says why. **Never edit a file without a backup.**
- The record is `05-application/00-intake/backup.yaml`; `MANIFEST.md` in the backup folder holds
  the restore commands. Append every edited file to its *Edited files* table as you go.
- Backups are never written inside the application directory or inside build output.
- If the user chose a branch: `git -C <APP_DIR> switch -c dbmig/<project>` **after** the backup
  is recorded. Never commit or push.

Restore: git mode `git -C <APP_DIR> restore --source <commit> -- <path>`; file-copy mode one
mirrored copy back (`cp -Rp <backup>/. <APP_DIR>/`). `diff -r` or `git diff <commit>` shows every
change at once.

At the end of Construction write `02-construction/app.diff`, the unified diff of every edit
(`git -C <APP_DIR> diff <commit>` in git mode; `diff -ruN <backup> <APP_DIR>` limited to the
scope in file-copy mode).

Gate: **"Approve the converted application?"** — present the diff summary and the conversion log;
record it as `app-construction`. In git mode the gate fingerprint includes the live git diff, so
an edit after approval marks the gate stale even when `app.diff` was not regenerated.

## Phase 3 — Validation & Testing

Invoke **`app-modernization-validation`**: compile, fix migration-caused failures, **boot the app
against the migrated target with schema validation on** (required for runnable ORM/framework apps
— the only check that proves entity mappings), run tests, and record a per-site verification
matrix. Compile and boot errors from the migration (types, error codes, driver APIs, ORM type
mappings) are expected, and fixing them is part of this module.

Gate: **"Approve the application validation results?"** Be explicit about what is `UNVERIFIED`;
record it as `app-validation`.

## Phase 4 — Operations & Cutover

Invoke **`app-modernization-operations`**: the application and the database must cut over
**together**, and the DB cutover runbook already treats the converted app build as a
precondition (its step 0.1). The skill produces `04-operations/app-cutover.md` — deploy
artifact + configuration (secrets by reference), ordering against the DB runbook, rollback,
post-cutover checks that exercise the *converted* code paths, and the open behavioural risks
with owners.

Gate: **"Approve the application cutover plan?"**; record it as `app-operations`.

## Gates are recorded

The four application gates live in the migration's `project.yaml`, next to the database gates:
`app-inception`, `app-construction`, `app-validation`, `app-operations`. They appear once
`00-intake/app-intake.md` exists. At each gate:

- Run `./dbmig gate status --project <P>` and present the application gate's **blockers**
  (missing artifacts, an earlier application gate not approved, open decisions) and
  **warnings** (for example the database Construction gate is not approved yet: the change plan
  relies on its conversion log).
- Offer `./dbmig review --project <P> --open`: its **Application** page shows the gates, the
  backup (mode, base commit or folder), the questionnaire answers and the per-file diff.
- Wait for the user's explicit approval, then record it:
  ```bash
  ./dbmig gate approve app-<phase> --project <P> --approved-by "<user's name>" --via chat \
      --note "<what the user said / conditions>"
  ```
  Never approve on the user's behalf. A rejected gate: `./dbmig gate reject app-<phase> ...
  --reason "<why>"`, then loop back.
- A stale gate (its files changed after approval) is re-presented and re-approved before the next
  one; `gate status` says what changed and how to fix it.
- Ambiguities become decisions: `./dbmig decision raise --phase app-<phase> --kind <kind>
  --question ... --option id=label ...`, answered with `./dbmig decision answer`. Open decisions
  block their gate.

## Safety

- Application source is user code: **editing it is a gated action**, gated at the Inception gate.
- Never edit build output. If a stray `.bak`/`.orig` is found there (a common leftover from ad-hoc
  conversions), report it rather than "fixing" it.
- Never commit or push on the user's behalf. In git mode the edits stay uncommitted (or on the
  local `dbmig/<project>` branch the user chose) for the user to review.
- Datasource files often hold **plaintext credentials**. Never echo secret values; show structure
  with the secret redacted and recommend environment variables or a secrets manager.
- If the target database is reachable, prefer validating identifiers against the live catalog over
  inferring them — read-only. This module never writes to a database.
