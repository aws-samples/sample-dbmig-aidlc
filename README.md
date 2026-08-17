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
- **SQL Server (source)**: [`python-tds`](https://python-tds.readthedocs.io/) (pure Python)
- **PostgreSQL (target)**: [`psycopg`](https://www.psycopg.org/) v3 with bundled libpq
- **MySQL (target)**: [`PyMySQL`](https://pymysql.readthedocs.io/) — pure Python

```bash
pip install -r scripts/requirements.txt
python -m dbmig test-connection --side both     # exits non-zero on failure
```

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
python -m dbmig inventory       --schema APP --project myproject

# 2) Extract object-units + build prompt bundles (Kiro then converts each to DDL)
python -m dbmig convert-schema  --schema APP --project myproject
#    optional subset:  --tables ORDERS,CUSTOMERS

# 3) Apply converted DDL — tables, indexes, PK/UK/CHECK (foreign keys + triggers
#    are deferred to after the data load)
python -m dbmig apply-schema    --schema APP --project myproject

# 4) Stored code objects (PL/SQL or T-SQL) — separate pass
python -m dbmig convert-code    --schema APP --project myproject
python -m dbmig apply-schema    --schema APP --project myproject --code

# 5) Migrate data (parallel COPY workers, PK-chunked, resumable)
python -m dbmig migrate-data    --schema APP --workers 8 --project myproject

# 6) Apply deferred foreign keys + triggers, now that the data is loaded
python -m dbmig apply-schema    --schema APP --project myproject --post-data

# 7) Reconcile source vs target
python -m dbmig compare         --schema APP --project myproject

# 8) Equivalence tests — Kiro generates cases from real data; run in a rolled-back txn
python -m dbmig gen-tests       --schema APP --project myproject
python -m dbmig run-tests       --schema APP --project myproject
```

Conversion or test failures are, by default (silent mode), logged to
`migrations/<project>/follow-up.yaml` and the run continues; use `--mode interactive` to be
prompted instead. For production-scale data movement use AWS DMS (the framework hands off to
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

## Repository layout

```
dbmig-aidlc/
├── skills/                              # the framework brain (Kiro skills)
│   ├── db-migration-orchestrator/       # ENTRY — interview + phase routing + gates
│   ├── db-migration-inception/          # assessment & planning
│   ├── db-migration-construction/       # schema + PL/SQL conversion
│   ├── db-migration-validation/         # data load + equivalence testing
│   ├── db-migration-operations/         # cutover, rollback, monitoring
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
│   ├── dbmig/                           # the Python package (python -m dbmig)
│   └── requirements.txt                 # pyyaml, oracledb, psycopg[binary], pymysql, python-tds
├── guides/                              # step-by-step guides, one per engine pair
├── templates/                           # connections + migration-config examples
├── sample-run-oracle-to-pg/             # a complete real run, captured end-to-end (example)
├── sample-run-sqlserver-to-pg/          # a second real run — SQL Server, two schemas, one project
└── migrations/                          # per-run workspaces (git-ignored; holds artifacts)
```

Two complete, real runs are archived for reference:
**[sample-run-oracle-to-pg/](sample-run-oracle-to-pg/)** (an Oracle `DEMO` schema) and
**[sample-run-sqlserver-to-pg/](sample-run-sqlserver-to-pg/)** (AdventureWorks `Person` +
`Sales` — 32 tables / ~395k rows / 6 views migrated under a single project using schema-scoped
manifests). Each holds every phase's artifacts (inventory, converted DDL/code, manifests,
apply/reconcile reports) so you can see the workflow's output without database access.

## Getting started

1. Install the toolkit dependencies (Python 3.9+):
   ```bash
   pip install -r scripts/requirements.txt
   ```
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

python -m dbmig inventory      --schema Person --project "$PROJECT"
python -m dbmig convert-schema  --schema Person --project "$PROJECT"
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
