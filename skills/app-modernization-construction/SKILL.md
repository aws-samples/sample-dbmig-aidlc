---
name: app-modernization-construction
description: >
  CONSTRUCTION phase of the optional application-modernization module: apply the APPROVED
  application changes from the change plan — embedded SQL, datasource/ORM configuration, entity
  mappings, stored-routine call sites, error handling and result-set typing — after backing up the
  application with ./dbmig app-backup (git when the app is in a clean git repo, otherwise a
  mirrored file copy; never .bak files in place). Engine-agnostic; reads the
  active pair's rules from engines/<pair>/app/. Invoked by app-modernization-orchestrator ONLY
  after the Inception change-plan gate is approved.
---

# Application Modernization — Construction (conversion)

Apply exactly what was approved. Nothing more.

**Precondition:** `01-assessment/change-plan.md` exists and the user has approved it. If either is
untrue, stop and return to the orchestrator's Inception gate. Approval may have been partial —
convert only the approved items and record the rest as deferred.

## Backup — before the first edit

Check the gate, then make the backup with one command:

```bash
./dbmig gate status --project <P>        # app-inception must be approved
./dbmig app-backup --project <P> --app <APP_DIR> [--mode auto|git|file-copy] [--scope <paths>]
```

`app-backup` warns (refuses with `run.enforce_gates: true`) when `app-inception` is not approved.
Do not work around the warning; get the approval.

- Use the mode and scope recorded at intake (`00-intake/app-intake.md`, or `app.intake` from the
  application questionnaire). `auto` is the default: **git when the app is in a clean git
  repository**, a file copy of the whole in-scope tree otherwise.
- **git mode**: the base commit is recorded; in-scope files git ignores are copied. Leave the
  edits uncommitted (or on the local `dbmig/<project>` branch the user chose); never commit or
  push.
- **file-copy mode**: the whole in-scope tree is copied once, before the first edit, to
  `05-application/backup/<timestamp>/`, so files touched later (boot-time or validation fixes)
  are already covered.
- If git was requested but cannot be used, `app-backup` falls back to a file copy and says why.
  **Never edit a file without a recorded backup.** If `app-backup` fails, stop and report it.
- Never write a backup inside the application directory or inside build output.
- Append every edited file to the *Edited files* table in the backup's `MANIFEST.md` as you go:
  relative path, bytes, why it changed.
- When done, write `02-construction/app.diff`: `git -C <APP_DIR> diff <commit> -- <scope>` in git
  mode, `diff -ruN <backup folder> <APP_DIR>` over the scope in file-copy mode.

Rationale: an in-place `.bak` clutters the source tree, can be picked up by builds and packaging,
and is easy to commit by accident. A mirrored tree keeps originals grouped, greppable and
restorable in one command:

```
# restore everything
(cd "$BK" && find . -type f ! -name MANIFEST.md -exec cp -p {} "<app>/{}" \;)
# review everything at once
diff -r "$BK" "<app>" | head -50
```

## Conversion order

Convert in this order so the build fails for one reason at a time:

1. **Build dependencies** — add the target driver, remove the source driver (or keep both
   temporarily if a rollback path is wanted; say which and why).
2. **Connectivity/config** — URL, driver class, ORM dialect, schema selector.
3. **Entity mappings** — table/column names, identifier quoting, generator strategies.
4. **Embedded SQL** — tier 1 and 2 first, then reconstructed tier 3.
5. **Stored-routine call sites** — renamed/flattened routines, procedure-vs-function call shape,
   OUT parameters, transaction ownership.
6. **Error handling** — error codes → target error identity.
7. **Result-set typing** — count types, column-name case, type reads.

## How to convert

- **Customer-specific app knowledge wins — highest precedence.** Read every `*.md` in
  `engines/<pair>/app/customer-specific/` (except `_index.md`) FIRST and treat it as the
  top authority; where it conflicts with the generic `app-sql-rules.md`/`app-config.yaml`,
  the customer file wins (rules there are marked "Override:"). This folder holds the
  customer's frameworks, datasource config, embedded-SQL conventions, error-code mappings
  and forbidden patterns.
- Apply the pair's `app-sql-rules.md` for dialect and behavioural rules, and `app-config.yaml`
  for driver/dialect/error/identity facts.
- **The migration's own decisions win.** Where `app-contract.md` records what this migration
  actually did — the error-code mapping, the flattened routine names, the target schema, the
  full-text redesign — follow it rather than the generic rule.
- **Never convert a tier-3 fragment in isolation.** Reconstruct the whole statement, convert it,
  then re-split it into the same fragments. `ROWNUM` before an `ORDER BY` is not `LIMIT` after it.
- **Preserve formatting and style.** Match the file's existing indentation, string-concatenation
  style and comment conventions. A conversion diff should show only semantic change.
- **Comment each behavioural change in place** so a reviewer sees the risk at the call site, e.g.
  `// MIGRATION: full-text search redesigned (Oracle Text -> PG GIN); ranking is ts_rank, not SCORE`
  (illustrative — use the active pair's construct names; the same pattern applies to e.g.
  SQL Server `CONTAINS` -> MySQL `MATCH..AGAINST`).
  Keep it to one line and do not restate the obvious for mechanical edits.
- **Do not silently "improve" code.** No refactoring, renaming or reformatting beyond what the
  migration requires. If something is clearly broken but out of scope, note it in the log.
- **Secrets:** when a connection string changes, do not echo the password. Prefer an environment
  variable or secrets-manager reference over a plaintext value, and say so in the log.
- If a site turns out to need a decision that the plan did not cover, **stop and ask** rather than
  guessing — then update the plan.

## Output — `02-construction/conversion-log.md`

- Per file: relative path, sites changed, backup (git base commit or backup folder).
- Per site: before/after, mechanical vs behavioural, and the contract row it satisfies.
- Behavioural changes collected in their own section with the risk restated and an owner.
- Deferred/blocked items and why.
- Any place where formatting or an unrelated defect was deliberately left alone.

Then hand off to `app-modernization-validation`. Do not claim success before the build runs.
