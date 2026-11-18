# Application modernization (separate, opt-in module)

After a database migration, the **application** still speaks the old dialect — embedded SQL,
datasource/ORM configuration, stored-routine call sites, error codes, result-set typing. An
optional module converts the application to match, driven by the migration's own artifacts
(its conversion log and validation carry-forwards) rather than generic rules.

**Like-for-like only.** The application keeps its architecture, framework and behaviour — the
module changes only what the database migration invalidated. It is *not* application refactoring:
no monolith-to-microservices decomposition, framework/language upgrades, ORM swaps, or general
cleanup — those are separate engagements.

- **Opt-in only — it never starts automatically.** Ask for it explicitly, e.g. *"convert my
  application to work with the migrated database"*. The `app-modernization-orchestrator` skill
  then asks for the application directory and which `migrations/<project>/` workspace to conform to.
- **Same AI-DLC phases, same gates**: Inception (inventory + **change plan**) → Construction →
  Validation (build/test) → Operations (app cutover). **Nothing is edited before the change plan
  is approved** — every proposed edit is previewed per site (current vs proposed code, risk class).
- **Recorded gates**: `app-inception`, `app-construction`, `app-validation` and
  `app-operations` sit in the migration's `project.yaml` next to the database gates, with the same
  `./dbmig gate` commands, fingerprints and stale explanations (see
  [Gates, decisions and the review site](gates-and-review.md)).
- **Backup before the first edit**, with `./dbmig app-backup` (see below). Never `.bak` files
  beside the originals.
- **Engine-pair extensible**: per-pair app rules live in `engines/<pair>/app/`
  (`app-config.yaml` + `app-sql-rules.md`), so new pairs need no skill changes. All four current
  pairs ship with app rules.

## Backup: git when possible, otherwise a file copy

```bash
./dbmig app-backup --project P --app /path/to/app [--mode auto|git|file-copy] [--scope src,pom.xml]
```

| Mode | When | What it does |
|---|---|---|
| `auto` (default) | always | `git` when possible, else `file-copy` |
| `git` | the app is in a git repository with a commit, git is installed, and the in-scope files have no uncommitted changes | Records the base commit and branch. Copies only in-scope files that git ignores (local config, for example), because git cannot restore them. Edits stay uncommitted, or go on a local `dbmig/<project>` branch if you ask; nothing is committed or pushed |
| `file-copy` | any app | Copies the whole in-scope tree once into `migrations/<P>/05-application/backup/<timestamp>/` (mirrored paths, timestamps and modes kept; build output and dependencies excluded) |

When `git` is asked for but cannot be used, the backup **falls back to a file copy** and says why,
so no file is edited without a backup. The record is `05-application/00-intake/backup.yaml`; the
backup folder's `MANIFEST.md` has the restore commands and the list of edited files.

| Restore | Command |
|---|---|
| git mode, one file | `git -C <app> restore --source <commit> -- <path>` |
| git mode, see every change | `git -C <app> diff <commit>` |
| file-copy mode | `cp -Rp <backup folder>/. <app>/` (then remove `MANIFEST.md`) |

In git mode the `app-construction` gate fingerprint includes the live `git diff` against the base
commit, so an edit after approval marks the gate stale even if `app.diff` was not regenerated.

## Optional application questionnaire

When the application team is not the team running the database migration, they can answer a
short Markdown questionnaire instead of answering in chat (one round; see
[the questionnaire page](questionnaire.md#application-questionnaire)):

```bash
./dbmig questionnaire new   --module app --project P
./dbmig questionnaire check --module app --project P [--apply]
```

It asks what a code scan cannot know: the app directory and scope, build and test commands, how
the app finds its database (names only), backup mode and branch policy, and conversion policies
that repeat across many call sites (vendor error codes, and per pair: case-insensitive search,
empty strings, sequences or identity read-back, identifier quoting). `--apply` records the
answers in `project.yaml` under `app:` and writes `05-application/00-intake/app-policies.md`,
which the application skills read as high-precedence context.

## Review

`./dbmig review --project P` adds an **Application** page once `05-application/` exists: the
application gates, the backup (mode, base commit or folder), the questionnaire answers, the phase
documents and every changed file from `02-construction/app.diff`.

## Pre-scan

`./dbmig app-scan --app-dir <dir> --project <P>` is the read-only pre-scan the Inception phase
uses: dialect SQL sites, routine calls, configuration, and an entity ↔ target column type
cross-check.

Two archived runs include the application step:
[`sample-run-oracle-to-pg/05-application/`](../sample-run-oracle-to-pg/05-application/) (Spring
Boot / JPA) and [`sample-run-sqlserver-to-pg/05-application/`](../sample-run-sqlserver-to-pg/05-application/)
(ASP.NET Core / EF Core).
