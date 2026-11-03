# dbmig-aidlc

An **AI-DLC-style database migration framework**. It turns a database migration into a
structured, agent-driven lifecycle — modeled on the AWS [AI-Driven Development Life
Cycle](https://aws.amazon.com/blogs/devops/ai-driven-development-life-cycle/) (AI-DLC),
where the AI acts as an *orchestrator* with clear phases, artifacts, and human decision
gates rather than a black-box code generator.

Supported engine pairs: **Oracle → PostgreSQL** and **SQL Server → PostgreSQL** (Aurora
PostgreSQL), and **Oracle → MySQL** and **SQL Server → MySQL** (Aurora MySQL). The package
uses a thin engine **adapter pattern** (`SourceEngine`/`TargetEngine` + a registry), so
additional pairs are added by composing existing source/target adapters (or adding one) plus
an `engines/<pair>/` definition + a playbook — with no changes to the orchestration, CLI, or
data-movement code.

> ⚠️ **Non-production use, and AI-generated output.** This toolkit is designed for
> **development, test, and proof-of-concept** migrations — not production. Its data mover is a
> dev/test loader (production data movement hands off to AWS DMS), and every artifact it
> produces — the conversion, the equivalence tests, and especially the **Operations guides
> (cutover runbook, rollback plan, monitoring checklist)** — is **AI-generated from your
> migration's context and is a starting point, not an authoritative runbook.** You are
> responsible for reviewing, adapting, and validating everything against your own environment,
> and testing it in a non-production environment, before relying on it. See
> [DISCLAIMER.txt](DISCLAIMER.txt).

## What it does

When you start a migration, the framework interviews you (source/target engines,
connection file, what to migrate), **tests connectivity** (via Python drivers — no native
client tools), then drives the migration through four phases. You approve at each gate.

| Phase | Skill | Output |
|---|---|---|
| **Inception** — Assessment & Planning | `db-migration-inception` | Connection check, object inventory, compatibility assessment, migration plan |
| **Construction** — Conversion | `db-migration-construction` | Converted schema + stored code (LLM-driven; playbook injected as context) |
| **Validation & Testing** | `db-migration-validation` | Test-data load (or AWS DMS hand-off) + equivalence test report (same input → same value / same net effect) |
| **Operations & Cutover** | `db-migration-operations` | Cutover plan, rollback plan, monitoring |

The entry point is the `db-migration-orchestrator` skill, which runs the intake interview
and routes between phases.

## Alternative start: continue from an existing AWS DMS Schema Conversion (DMS SC)

Sometimes the customer has **already run AWS DMS Schema Conversion**, applied the converted
schema to the target, and just needs to *continue* — the conversion is rarely 100% clean, so
DMS SC leaves *action items* on some objects. Instead of converting from scratch, point the
framework at the **local DMS SC project folder** and it will import, triage, and continue.

`dbmig import-dms-sc` parses the DMS SC project (engine- and schema-generic) and classifies
every object into three dispositions:

| Disposition | Meaning | What happens |
|---|---|---|
| **ACCEPT** | no action items | keep the DMS SC conversion as-is |
| **VERIFY** | `5444` ML/GenAI or LOW/MEDIUM advisories | keep, but **prove** it (equivalence tests); tracked in a ledger so it is not re-verified |
| **MANUAL** | CRITICAL/HIGH or "convert manually" | reconvert via the construction skill |

Because DMS SC already applied the schema, the toolkit also **reconciles against the live
target** and **prepares it for the data load** (drop load-hostile secondary objects, load,
recreate — keeping primary/unique keys):

```bash
./dbmig import-dms-sc         --dms-sc-dir <PATH> --project <P>   # import + triage (ACCEPT/VERIFY/MANUAL)
./dbmig diff-target           --schema <S> --project <P>         # reconcile vs LIVE target (MATCH/MISSING/UNMATCHED/EXTRA)
./dbmig capture-target-objects --schema <S> --project <P>        # snapshot FKs/indexes/triggers -> drop/restore scripts
./dbmig pre-load-drop         --schema <S> --project <P> --apply # before the data load
#   … load data (dbmig migrate-data, or an AWS DMS task) …
./dbmig post-load-restore     --schema <S> --project <P> --apply # after the data load; reconciles
./dbmig verify                --schema <S> --project <P>         # list/record VERIFY sign-off
```

Each run refreshes a human-readable, phase-aligned **`migrations/<project>/migration-report.md`**
so anyone can see what has been done and what to be aware of. This path is driven by the
`db-migration-dms-sc-ingest` skill (reached from the orchestrator's intake). See
**[docs/dms-sc-import-design.md](docs/dms-sc-import-design.md)**.

### Getting the DMS SC project onto your machine (copy from S3)

DMS Schema Conversion keeps the project files (the `s-*/` source tree, `t-*/` target tree,
`action-items/`, and `apply-result/`) in the **S3 bucket associated with the DMS SC instance
profile**, under a prefix named after your migration project. Copy that prefix to a local
folder (skip the `.zip`/`.pdf` report exports) and point `import-dms-sc` at it:

```bash
# find the bucket + your project prefix
aws s3 ls s3://<your-dms-sc-bucket>/

# copy the project locally (exclude the report exports)
aws s3 cp s3://<your-dms-sc-bucket>/<migration-project-name>/ ./dms-sc-project/ \
  --recursive --exclude "*.zip" --exclude "*.pdf"

./dbmig import-dms-sc --dms-sc-dir ./dms-sc-project --project <P>
```

The framework reads the local folder only — it does not call the DMS API — so you fully
control what is imported. Re-copy after a fresh DMS SC *apply* to refresh `apply-result/`.

### Sample prompts

**Fresh migration (you have NOT used DMS SC)** — start from the source database and let the
framework convert:

- *"Start a database migration from Oracle to PostgreSQL."*
- *"Migrate my SQL Server database to Aurora MySQL."*
- *"Convert my Oracle schema `APP` to PostgreSQL and validate it."*

**Continue from an existing DMS SC conversion (you HAVE used DMS SC and applied it)** — point
the framework at the local project folder you copied from S3:

- *"I already ran AWS DMS Schema Conversion and applied it to the target. Import my DMS SC
  project at `./dms-sc-project` and continue."*
- *"Continue from an existing DMS SC conversion — the project folder is at `~/dms/adventureworks`;
  triage it, reconcile against the live target, and prepare it for the data load."*
- *"Import the DMS SC project in `./dms-sc-project`, show me the ACCEPT/VERIFY/MANUAL triage,
  then diff it against the live target."*

## Optional: application modernization (separate, opt-in module)

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
- **Backups are a mirrored tree**, `migrations/<project>/05-application/backup/<timestamp>/…`,
  never `.bak` files scattered beside the originals.
- **Engine-pair extensible**: per-pair app rules live in `engines/<pair>/app/`
  (`app-config.yaml` + `app-sql-rules.md`), so new pairs need no skill changes. All four current
  pairs ship with app rules.

## How it maps to AI-DLC

AI-DLC positions AI as the central collaborator that **plans and executes while humans make
the critical decisions**, organized into phases with persistent, traceable artifacts. This
framework mirrors that loop: the orchestrator plans, asks for context, and implements only
after you approve each phase gate.

For the full mapping — the AI-DLC mental model on a migration, the phase breakdown, the
"Units of Work"/"bolts" vocabulary, and how quality and traceability are realized — see
**[DB-MIGRATION-AIDLC.md](DB-MIGRATION-AIDLC.md)**.

## Connecting to databases — pure Python, no native tools

The `dbmig` toolkit (`scripts/dbmig/`) connects with **Python drivers** — no `sqlplus` or
`psql` install required:

- **Oracle (source)**: [`oracledb`](https://python-oracledb.readthedocs.io/) in *thin mode*
  (Oracle 12.1+). **Oracle 11.2** is supported in *thick mode*: set `driver_mode: thick` on
  the source connection and install Oracle Instant Client 19+ (x86-64 Linux/Windows, or an
  Intel Mac; Apple Silicon has no Instant Client that reaches 11.2)
- **SQL Server (source)**: [`python-tds`](https://python-tds.readthedocs.io/) (pure Python),
  SQL Server **2008** and later
- **PostgreSQL (target)**: [`psycopg`](https://www.psycopg.org/) v3 with bundled libpq
- **MySQL (target)**: [`PyMySQL`](https://pymysql.readthedocs.io/) — pure Python

```bash
# one-time: an isolated virtual environment inside the repo (see "Getting started")
python3 -m venv .venv && .venv/bin/pip install -e scripts/
./dbmig test-connection --side both     # exits non-zero on failure
```

Run every command through the **`./dbmig`** launcher at the repo root. It uses the repo's
`.venv` automatically (no `activate` needed), so config and `migrations/` resolve from the repo
root. With the venv activated, the plain `dbmig` command works too. `--conn <path>` /
`--config <path>` (before the command) point at a connections file / migration config
elsewhere.

**Credentials in AWS Secrets Manager?** `connections.yaml` needs no special support: give Kiro
the secret name and AWS profile/region and it reads the secret with the AWS CLI, writes the
non-secret fields (host, port, user, service/database) into `connections.yaml`, and keeps the
password as a `${VAR}` reference supplied from the secret per command — it is never written
to disk or echoed.

## Schema conversion is LLM-driven — and the LLM is Kiro

There is **no datatype rule engine**. The `dbmig` package does the deterministic work
(extract source object-units, build prompt bundles, apply DDL, copy data, reconcile) and
**Kiro performs the actual schema/code conversion** via the `db-migration-construction`
skill. The package makes **no LLM API calls** and runs standalone for every other step.

Conversion works on **object-units** — a table together with its indexes, constraints
(PK/UK/FK/CHECK), DML triggers, comments and grants — so the conversion is holistic rather
than layer-by-layer. The active pair's `engines/<source>-to-<target>/` directory (datatype
map) and the matching `<pair>-playbook` references are injected into the prompt as **context
material**, not executed as rules.

```bash
# 1) Inspect / plan
./dbmig inventory       --schema APP --project myproject

# 2) Extract object-units + build prompt bundles (Kiro then converts each to DDL)
./dbmig convert-schema  --schema APP --project myproject
#    optional subset:  --tables ORDERS,CUSTOMERS

# 3) Apply converted DDL — tables, indexes, PK/UK/CHECK (foreign keys + triggers
#    are deferred to after the data load)
./dbmig apply-schema    --schema APP --project myproject

# 4) Stored code objects (PL/SQL or T-SQL) — separate pass
./dbmig convert-code    --schema APP --project myproject
./dbmig apply-schema    --schema APP --project myproject --code

# 5) Migrate data (parallel COPY workers, PK-chunked, resumable)
./dbmig migrate-data    --schema APP --workers 8 --project myproject
#    cloud-to-cloud fast path (PostgreSQL target): let the target read directly from
#    the source via a foreign data wrapper (oracle_fdw / tds_fdw) instead of pulling
#    every row through this host — ideal when dbmig runs on-prem across a slow VPN:
#      ./dbmig migrate-data --schema APP --method fdw --shards 16 --workers 16 --project myproject

# 6) Apply deferred foreign keys + triggers, now that the data is loaded
./dbmig apply-schema    --schema APP --project myproject --post-data

# 7) Reconcile source vs target
./dbmig compare         --schema APP --project myproject

# 8) Equivalence tests — Kiro generates cases from real data; run in a rolled-back txn
./dbmig gen-tests       --schema APP --project myproject
./dbmig run-tests       --schema APP --project myproject

# 9) Cutover: sync identity sequences to the loaded data (dry-run report, then --apply)
./dbmig reset-identity  --schema APP --project myproject [--apply]
```

Conversion or test failures are, by default (silent mode), logged to
`migrations/<project>/follow-up.yaml` and the run continues; use `--mode interactive` to be
prompted instead. When a re-run of `run-tests` / `compare` passes, the matching follow-up
items are set to `resolved` automatically. `gen-tests` tags objects whose source tables are
all empty as `LOW_COVERAGE`, and `run-tests` reports them separately. For production-scale data movement use AWS DMS (the framework hands off to
it); the built-in `migrate-data` is for dev/test loads and reconciliation.

## Step-by-step guides

Guides are organized **per engine pair**. For a complete walkthrough — prerequisites, setup,
the four phases, the Kiro conversion hand-off, data migration, validation, cutover, command
reference, and troubleshooting — see:

- **[guides/oracle-to-postgresql.md](guides/oracle-to-postgresql.md)** — Oracle → PostgreSQL
- **[guides/oracle-to-mysql.md](guides/oracle-to-mysql.md)** — Oracle → MySQL
- **[guides/sqlserver-to-postgresql.md](guides/sqlserver-to-postgresql.md)** — SQL Server → PostgreSQL
- **[guides/sqlserver-to-mysql.md](guides/sqlserver-to-mysql.md)** — SQL Server → MySQL
- **[guides/README.md](guides/README.md)** — index of all engine-pair guides

Cross-cutting (not pair-specific):

- **[guides/database-users-and-permissions.md](guides/database-users-and-permissions.md)** —
  how to create a least-privilege **read-only source user** and a **read-write target user**,
  the exact privileges each engine needs, and the **extra permissions for the PostgreSQL FDW
  method** (includes a warning that a read-only user which can execute data-modifying
  procedures/functions can still change data).

## Repository layout

```
dbmig-aidlc/
├── skills/                              # the framework brain (Kiro skills)
│   ├── db-migration-orchestrator/       # ENTRY — interview + phase routing + gates
│   ├── db-migration-inception/          # assessment & planning
│   ├── db-migration-construction/       # schema + PL/SQL conversion
│   ├── db-migration-validation/         # data load + equivalence testing
│   ├── db-migration-operations/         # cutover, rollback, monitoring
│   ├── db-migration-dms-sc-ingest/      # ALT entry: import an existing AWS DMS SC project
│   ├── app-modernization-orchestrator/  # OPTIONAL app-code module — entry (opt-in, gated)
│   ├── app-modernization-inception/     #   Inception: scan + classify impacted app sites
│   ├── app-modernization-construction/  #   Construction: apply approved edits + mirrored backups
│   ├── app-modernization-validation/    #   Validation: compile, fix, test, verification matrix
│   ├── app-modernization-operations/    #   Operations: app cutover plan feeding the DB runbook
│   ├── oracle-to-postgresql-playbook/   # AWS playbook → granular references
│   ├── oracle-to-mysql-playbook/        # AWS playbook → granular references
│   ├── sqlserver-to-postgresql-playbook/ # AWS playbook → granular references
│   └── sqlserver-to-mysql-playbook/     # AWS playbook → granular references
├── engines/
│   ├── oracle-to-postgresql/            # engine.yaml, datatype-map.yaml, checks/, app/
│   ├── oracle-to-mysql/                 # engine.yaml, datatype-map.yaml, checks/
│   ├── sqlserver-to-postgresql/         # engine.yaml, datatype-map.yaml, checks/
│   └── sqlserver-to-mysql/              # engine.yaml, datatype-map.yaml, checks/
├── scripts/
│   ├── dbmig/                           # the Python package (./dbmig)
│   └── requirements.txt                 # pyyaml, oracledb, psycopg[binary], pymysql, python-tds
├── guides/                              # step-by-step guides, one per engine pair
├── templates/                           # connections + migration-config examples
├── sample-run-oracle-to-pg/             # sample run 1: converted purely by dbmig-aidlc (Oracle DEMO)
├── sample-run-sqlserver-to-pg/          # sample run 2: converted purely by dbmig-aidlc (SQL Server BobsUsedBookStore + .NET app)
├── sample-run-dms-sc-sqlserver-to-pg/   # sample run 3: CONTINUE from AWS DMS SC output (SQL Server AdventureWorks)
└── migrations/                          # per-run workspaces (git-ignored; holds artifacts)
```

Three complete, real runs are archived for reference:
**[sample-run-oracle-to-pg/](sample-run-oracle-to-pg/)** — Oracle `DEMO` **converted purely by
dbmig-aidlc**, all four AI-DLC phases plus modernization of the Spring Boot / JPA app;
**[sample-run-sqlserver-to-pg/](sample-run-sqlserver-to-pg/)** — SQL Server `BobsUsedBookStore`
converted from scratch plus the ASP.NET Core / EF Core app; and
**[sample-run-dms-sc-sqlserver-to-pg/](sample-run-dms-sc-sqlserver-to-pg/)** — a run that
**starts from AWS DMS Schema Conversion output** and works forward (SQL Server
`AdventureWorks` `Person` + `HumanResources`: import → ACCEPT/VERIFY/MANUAL triage →
`diff-target` reconciliation → MANUAL reconversion → secondary-object drop/load/restore →
`compare` + equivalence tests → VERIFY sign-off). All are masked
(no real hosts/credentials) and hold each phase's artifacts so you can see the workflow's
output without database access.

## Getting started

1. Create an **isolated virtual environment** in the repo and install the toolkit into it
   (**Python 3.10+** — check with `python3 --version`; `venv` is built in, nothing extra to install):
   ```bash
   cd dbmig-aidlc
   python3 -m venv .venv                 # .venv/ is git-ignored
   .venv/bin/pip install -e scripts/     # Windows: .venv\Scripts\pip install -e scripts/
   ./dbmig --version                     # the launcher uses .venv automatically
   ```
   **Why a venv:** the toolkit needs recent driver and security-library versions
   (e.g. `cryptography>=46`, `pyOpenSSL>=26` for CVE fixes). Installing them into your
   system or user Python could upgrade packages that other tools on your machine depend on.
   Inside `.venv` they are isolated to this repo; `rm -rf .venv` removes everything.
   Do **not** run `pip install` against your global Python for this toolkit. (Newer
   macOS/Homebrew and Debian/Ubuntu Pythons refuse it anyway with
   `externally-managed-environment`.) If you use [uv](https://docs.astral.sh/uv/),
   `uv venv && uv pip install -e scripts/` does the same thing faster.
2. Copy the templates and fill in your connection details:
   ```bash
   cp templates/connections.example.yaml connections.yaml
   cp templates/migration-config.example.yaml migration-config.yaml
   ```
   Keep secrets out of the file — use environment-variable references (see the template).
3. Kiro workspace — **ships with the repo, nothing to set up**. The project-local steering
   file at [`.kiro/steering/dbmig-aidlc.md`](.kiro/steering/dbmig-aidlc.md) is included in the
   clone, so the moment you run `kiro-cli chat` in this folder Kiro automatically recognizes it
   as an AI-DLC migration project and follows the phase/gate discipline. It is workspace-local —
   nothing touches your global `~/.kiro/`. Run `/context show` in the chat to confirm
   `.kiro/steering/dbmig-aidlc.md` is loaded.
   > ⚠️ **Start Kiro from the `dbmig-aidlc` folder itself** (`cd dbmig-aidlc && kiro-cli chat`),
   > not from its parent or your home directory. Kiro loads project steering only from the
   > folder it was started in; started elsewhere, it will not know about this framework's
   > phases, gates, or safety rules. If `/context show` does not list
   > `.kiro/steering/dbmig-aidlc.md`, exit and restart from the right folder.

   **Using Claude Code instead?** Also supported, from the same folder (`cd dbmig-aidlc &&
   claude`). The root [`CLAUDE.md`](CLAUDE.md) imports the same steering file (one source of
   truth), and `.claude/skills/` exposes the 15 framework skills to Claude Code as thin
   pointers to `skills/`. Check with `/memory` (or `/context`) that `CLAUDE.md` and the
   steering file are loaded. Maintainers: after adding/renaming a skill or changing its
   `description`, run `python3 scripts/sync-claude-skills.py` (a unit test fails if stale).
4. In Kiro, start a migration — e.g. *"start a database migration from Oracle to
   PostgreSQL"*. The `db-migration-orchestrator` skill will take over, test the
   connections, and walk you through the phases (Kiro performs the schema conversion
   itself; the `dbmig` package handles everything else).

## Run workspaces & multiple runs

Each run's artifacts (inventory, prompts, converted DDL/code, reports, data state) live under a
**per-run workspace**: `migrations/<project>/`. Two settings control where a run is written, so you
can keep runs isolated and re-run without overwriting a previous one:

- **`--project <name>`** (or `project:` in `migration-config.yaml`) — names the workspace folder.
  Precedence is: the CLI `--project` flag, else the config's `project:`, else `default`. The value is
  **sanitized into a safe folder name** (quotes dropped, spaces → dashes, other unsafe characters →
  dashes), so e.g. `--project "my's test run"` becomes `migrations/mys-test-run/`. Pass the **same
  project to every command** in a run so the phases share one workspace.
- **`DBMIG_MIGRATIONS_DIR`** — relocates the whole `migrations/` root anywhere (e.g. outside the repo),
  which is handy for throwaway runs you can delete freely.

To keep multiple runs from colliding, give each run a distinct project — a date-stamp is a simple
convention (the toolkit does not add one for you):

```bash
export PROJECT="adventureworks-$(date +%Y%m%d-%H%M%S)"   # unique per run
# optional: export DBMIG_MIGRATIONS_DIR=/tmp/dbmig-runs   # isolate outside the repo

./dbmig inventory      --schema Person --project "$PROJECT"
./dbmig convert-schema  --schema Person --project "$PROJECT"
# … apply-schema / convert-code / migrate-data / apply-schema --post-data / compare / gen-tests / run-tests …
```

A single project can hold several schemas — manifests and inventories are schema-scoped
(`manifest-<SCHEMA>.yaml`, `inventory-<SCHEMA>.yaml`), so `--project` is the whole run and `--schema`
selects the schema within it.

Two guardrails learned from real runs: `convert-schema`/`convert-code` **warn when regenerating a
manifest that already shows progress** (reusing a `--project` across runs mixes artifacts and
follow-up items silently), and `apply-schema` **cross-checks the catalog after applying** — DDL
qualified with the wrong schema/database applies "successfully" into the wrong namespace and is
reported as `SCHEMA MISMATCH` instead of surfacing later at the data load.

## Security & safety notes

- `connections.yaml`, `migration-config.yaml`, and `migrations/` are git-ignored by default
  so credentials and run artifacts are never committed.
- Prefer environment-variable references over plaintext passwords in the connection file.
- The framework treats schema/data changes as gated actions and asks before destructive
  operations on the target.

## Architecture

For a professional, easy-to-follow description of how the framework is structured — the
agent/skill layer, the Python toolkit, the engine adapter pattern, the conversion hand-off to
Kiro, and how data flows through the four phases — see **[ARCHITECTURE.md](ARCHITECTURE.md)**.

## Status

Four engine pairs are supported: **Oracle → PostgreSQL**, **Oracle → MySQL**,
**SQL Server → PostgreSQL**, and **SQL Server → MySQL**. The playbook references under
`skills/<pair>-playbook/references/` are distilled from the corresponding AWS migration
playbooks and are provided as reference only — **test everything in a non-production
environment first.**

## License

Licensed under the **MIT-0** (MIT No Attribution) license — the standard license for AWS sample
code. See [LICENSE](LICENSE). You may copy code from this repository into your own projects
without reproducing the license or attribution.
