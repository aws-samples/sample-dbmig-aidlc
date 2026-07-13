# Migration Guide — Oracle → PostgreSQL

> **Engine pair:** `oracle` (source) → `postgresql` (target, Aurora PostgreSQL compatible)
> **Engine definition:** [`engines/oracle-to-postgresql/`](../engines/oracle-to-postgresql/)
> **Playbook:** [`skills/oracle-to-postgresql-playbook/`](../skills/oracle-to-postgresql-playbook/)
>
> This is one engine-pair guide. The framework is engine-pluggable — other source→target
> pairs live alongside this one under `guides/<source>-to-<target>.md`. See the
> [guides index](README.md). The orchestration, CLI, and lifecycle are the same across
> pairs; only the engine definition, playbook references, and the source/target drivers
> differ.

A step-by-step guide to migrating an **Oracle** schema to **PostgreSQL** (Aurora PostgreSQL
compatible) with **dbmig-aidlc**.

The framework has two cooperating parts:

- **`dbmig` Python package** (`scripts/dbmig/`) — does all the deterministic work
  (connect, inventory, extract, apply, copy data, reconcile). Runs standalone with Python
  drivers; **no `sqlplus`/`psql` needed**.
- **Kiro skills** (`skills/`) — drive the AI-DLC lifecycle and **perform the schema
  conversion itself**. The LLM is Kiro: `dbmig` prepares prompt bundles, Kiro converts them
  to PostgreSQL DDL, `dbmig` applies them.

You can run the whole thing **conversationally through Kiro** (recommended) or **drive the
`dbmig` CLI yourself** and only hand the conversion step to Kiro. Both are covered below.

---

## 1. Prerequisites

- **Python 3.9+**
- Network access from your machine to the **source Oracle** and **target PostgreSQL**
  endpoints.
- A target PostgreSQL/Aurora database you can create objects in.

Install the toolkit dependencies:

```bash
pip install -r scripts/requirements.txt
```

This installs `oracledb` (thin mode — no Oracle client install), `psycopg[binary]`
(PostgreSQL driver with bundled libpq), and `pyyaml`.

Verify the CLI is available (run from the repo root):

```bash
python -m dbmig --version
python -m dbmig --help
```

> Run all commands from the **repository root** so `./connections.yaml` and the skill/engine
> context are found. To keep configs elsewhere, set `CONN_FILE` and `MIGRATION_CONFIG`.

---

## 2. Configure connections and scope

Copy the templates and fill them in:

```bash
cp templates/connections.example.yaml connections.yaml
cp templates/migration-config.example.yaml migration-config.yaml
```

Both files are **git-ignored**. Keep secrets out of them — use `${ENV_VAR}` references.

### connections.yaml

```yaml
source:
  engine: oracle
  version: "19c"
  host: ${ORA_HOST}
  port: 1521
  service_name: ${ORA_SERVICE}   # or set 'sid:' instead
  username: ${ORA_USER}
  password: ${ORA_PASSWORD}

target:
  engine: postgresql
  version: "16"
  host: ${PG_HOST}
  port: 5432
  database: ${PG_DATABASE}
  username: ${PG_USER}
  password: ${PG_PASSWORD}
  default_schema: public
  sslmode: require
```

Export the referenced environment variables before running:

```bash
export ORA_HOST=oracle.example.com ORA_SERVICE=ORCLPDB1 ORA_USER=app ORA_PASSWORD=...
export PG_HOST=mydb.cluster-xxxx.us-west-2.rds.amazonaws.com PG_DATABASE=appdb \
       PG_USER=app PG_PASSWORD=...
```

### migration-config.yaml

Set the schema(s), strategy, and conversion/testing options. The conversion is performed by
Kiro (`llm.provider: kiro`) — no API keys are needed.

```yaml
project: myproject
scope:
  schemas: [APP]
strategy:
  mode: full                 # schema_only | data_only | full
  identifier_case: lower_case
llm:
  provider: kiro             # Kiro converts; dbmig makes no API calls
  batch_row_threshold: 100000
  batch_max_units: 5
testing:
  data_load: framework       # framework (dbmig load) | dms (you run AWS DMS)
```

---

## 3. Test connectivity (pre-flight)

```bash
python -m dbmig test-connection --side both
```

You should see both source and target connect with a reported version. The command exits
non-zero on failure — fix connectivity before continuing. (If a driver is missing it tells
you to `pip install -r scripts/requirements.txt`.)

---

## 4. (Optional) Add customer-specific knowledge — highest precedence

If this customer has their own conventions or constraints (naming, datatype overrides,
available extensions, app/ORM expectations, forbidden patterns), capture them in:

```
skills/oracle-to-postgresql-playbook/references/customer-specific/
```

Create one Markdown file per topic (see `_index.md` and `example-overrides.md` there).
These rules are injected at the **top of every conversion prompt** and **override** the
general playbook when they conflict. Example `datatype-overrides.md`:

```markdown
# Datatype overrides
- Override: Oracle NUMBER(1) flags -> PostgreSQL boolean.
- Override: money columns -> numeric(19,4), never double precision.
- postgis is NOT available; flag any SDO_GEOMETRY for redesign.
```

This is the right place to encode decisions so conversions stay consistent across the run.

---

## 5. Run the migration

### Option A — Conversationally through Kiro (recommended)

In Kiro, say:

> "Start a database migration from Oracle to PostgreSQL."

The **`db-migration-orchestrator`** skill takes over: it runs the intake interview, tests
connectivity, and walks you through the four phases, stopping at a **human approval gate**
after each. Kiro runs the `dbmig` commands for you and performs the conversion step itself.
Approve each phase to advance.

### Option B — Drive the CLI yourself

The full pipeline, phase by phase:

```bash
# Phase 1 — Inception: assess the source
python -m dbmig inventory       --schema APP --project myproject

# Phase 2 — Construction: extract object-units + build prompt bundles
python -m dbmig convert-schema  --schema APP --project myproject
#   ↳ now have Kiro convert each prompt bundle (see 5.1 below)
python -m dbmig apply-schema    --schema APP --project myproject

#   PL/SQL code objects — separate pass
python -m dbmig convert-code    --schema APP --project myproject
#   ↳ Kiro converts the code prompts
python -m dbmig apply-schema    --schema APP --project myproject --code

# Phase 3 — Validation: load test data, apply deferred FKs + triggers, then reconcile
python -m dbmig migrate-data    --schema APP --workers 8 --project myproject
python -m dbmig apply-schema    --schema APP --project myproject --post-data
python -m dbmig compare         --schema APP --project myproject

# Phase 4 — Operations: cutover/rollback/monitoring (plan via the operations skill)
```

#### 5.1 The conversion hand-off (how Kiro converts)

`convert-schema` does **not** call an LLM. It writes, under
`migrations/myproject/02-construction/`:

- `prompts/APP/*.prompt.md` — one bundle per table (or per small-table batch), with the
  construction skill, datatype map, customer-specific rules, and the source object-unit DDL
  injected as context.
- `manifest.yaml` — one row per unit: `name, prompt_file, output_file, status: pending`.

Then **Kiro** (via the `db-migration-construction` skill) does the conversion: for each
`pending` unit it reads the prompt, writes PostgreSQL DDL to the unit's
`ddl/<schema>/<table>.sql`, and sets `status: converted`. `apply-schema` then applies all
converted DDL to the target.

If you are driving the CLI manually, ask Kiro: *"convert the pending units in
migrations/myproject/02-construction"* — it follows the construction skill.

#### 5.2 What "object-unit" means

Conversion is **holistic**, not layer-by-layer. Each unit is a table **with** its indexes,
constraints (PK/UK/FK/CHECK), DML triggers, comments, and grants — so Kiro can make
whole-table decisions (e.g. the right index type given a constraint). Small tables are
batched into one prompt to reduce round-trips; large tables get their own.

#### 5.2.1 Code objects + the package naming-conflict check

`convert-code` handles PL/SQL (packages, procedures, functions) as a separate pass. Because
PostgreSQL has no packages, each package subprogram is flattened to a `demo.<package>_<subprogram>`
routine. The underscore join is **not unique** — `BOOK_PKG.GET_X` and `BOOK.PKG_GET_X` both
become `book_pkg_get_x`, and a package routine can shadow a standalone one. `convert-code`
therefore runs an automatic **naming-conflict check** (via `ALL_PROCEDURES`): collisions are
printed and recorded to `follow-up.yaml` (kind `naming_conflict`) so you disambiguate them
(e.g. a `<package>$<subprogram>` separator, or a rename) before relying on the converted code.
See [`engines/oracle-to-postgresql/checks/package-naming.md`](../engines/oracle-to-postgresql/checks/package-naming.md).

#### 5.3 Applying DDL — ordering + automated error-retry loop

`apply-schema` is **status-aware and resumable**: it skips units already `applied` (so
re-running never re-triggers "already exists") and applies units **multi-pass** so a foreign
key to a not-yet-created table resolves on a later pass.

**Foreign keys and triggers are deferred to after the data load.** The default
`apply-schema` applies tables, indexes, and PK/UK/CHECK constraints (and trigger *functions*),
but **not** `FOREIGN KEY` constraints or `CREATE TRIGGER` statements — those are held back and
applied by `apply-schema --post-data` *after* `migrate-data`. This matters because an enforced
foreign key would force the loader to insert parents before children, and a row trigger would
fire during the load and **rewrite** the data being inserted (e.g. a `search_text`-maintenance
trigger), diverging the target from the source. Deferral is tracked in a separate `post_status`
field, so the post-data pass is independently idempotent and resumable.

When a unit's DDL **fails to run on PostgreSQL**, an **automated retry loop** kicks in
instead of stopping for a human:

1. The exact PostgreSQL error is captured to `apply_report.yaml`, and a **remediation
   prompt** is written to `02-construction/retries/<SCHEMA>/<unit>.retry.md` — the original
   conversion prompt **plus the failed DDL plus the error**.
2. The command prints **`RETRY_AVAILABLE`**. Kiro reads each remediation prompt, produces
   **corrected** DDL, overwrites the unit's `.sql`, and `apply-schema` runs again.
3. This repeats up to **`llm.max_retries`** attempts per unit (default 3, set in
   `migration-config.yaml`; override per run with `--max-retries N`).
4. A unit that still fails after the cap is marked **`needs_human`** and the command prints
   **`MAX_RETRIES_EXHAUSTED`** — only then is human review needed.

So in normal operation Kiro self-heals failed conversions within the retry budget; you only
get pulled in for the genuinely hard cases. Target a single unit while iterating with
`--tables ORDERS`. The manifest tracks `status` (`applied`/`failed`/`needs_human`),
`attempts`, and `last_error` per unit.

---

## 6. Migrate data

```bash
# Whole schema, 8 parallel workers
python -m dbmig migrate-data --schema APP --workers 8 --project myproject

# A subset, with tuning
python -m dbmig migrate-data --schema APP --tables ORDERS,CUSTOMERS \
       --batch-size 50000 --truncate --project myproject
```

- **Foreign-key aware order**: tables are loaded in dependency **tiers** (parents before
  children) computed from the source's foreign keys, so you don't have to order `--tables`
  yourself; tables within a tier are copied in parallel.
- One worker per table (ThreadPoolExecutor), each with its own connections.
- Large tables stream in **PK-ordered chunks** via the COPY protocol.
- **Identity/sequence reset**: after a table loads, its PostgreSQL `IDENTITY` sequence (or
  MySQL `AUTO_INCREMENT`) is advanced to `MAX(key)`, so application inserts after the load
  don't collide with migrated keys.
- **Resumable**: the last copied PK is tracked under `migrations/<project>/data/_state/`; a
  re-run continues where it left off. Tables without a single-column PK are copied whole
  (use `--truncate` to reset them first).

> `migrate-data` is for **dev/test** loads and reconciliation. For **production-scale** data
> movement (large volumes, minimal downtime, change data capture), use **AWS DMS** — set
> `testing.data_load: dms` and load externally, then skip straight to `compare`.

---

## 7. Validate equivalence

Prove the target behaves like the source, in two layers.

### 7.1 Data reconciliation
```bash
python -m dbmig compare --schema APP --project myproject
```
Checks per-table row counts → `03-validation/reconcile_report.yaml`. Mismatches are recorded
to the follow-up log (silent mode) rather than aborting the run.

### 7.2 Code equivalence — functions, procedures, packages (LLM-generated tests)

This proves *same input → same return value* (functions) and *same input → same net effect*
(procedures), using **test cases Kiro generates from real data**, executed **inside a
transaction that is rolled back** (representative but non-destructive).

```bash
# 1) Prepare: extract callables + sample REAL rows + build test-gen prompts
python -m dbmig gen-tests  --schema APP --project myproject
#    ↳ Kiro writes a test spec (.test.yaml) per object to 03-validation/tests/APP/,
#      using real sampled values; sets status 'generated' in test-manifest.yaml
# 2) Run: execute each case on source + target in a rolled-back transaction, compare
python -m dbmig run-tests  --schema APP --project myproject
```

- **Functions**: the call runs on both engines and the return value is compared (with
  `testing.equivalence.float_tolerance` / whitespace normalization).
- **Procedures**: Kiro chooses **probe queries** that capture the procedure's effect; the
  runner snapshots each probe **before and after** the call on each engine and compares the
  **delta** — so the net effect must match even though nothing is returned.
- Results → `03-validation/equivalence-report.yaml` (+ `.md`).
- *Caveat*: a procedure that issues its own `COMMIT` can't be rolled back — test those only
  against a disposable target.

Or just ask Kiro: *"run the validation phase for myproject"* and it drives gen-tests → spec
generation → run-tests for you.

### 7.3 Run modes & the follow-up log

How **failures** (conversion or test) are handled is controlled by `run.mode` in
`migration-config.yaml` (override with `--mode` or `DBMIG_MODE`):

- **`silent`** (default) — every failure is appended to
  `migrations/myproject/follow-up.yaml` (+ a readable `follow-up.md`) and the run
  **continues**. You triage the open items later. This keeps long migrations moving instead
  of stopping on the first problem.
- **`interactive`** — additionally prompts for input/correction (on a TTY) and exits
  non-zero so failures are addressed immediately.

Each follow-up item records the phase, kind (`conversion_failure`, `data_mismatch`,
`test_failure`), object, and detail — your post-run to-do list.

---

## 8. Cutover and operations

Use the **`db-migration-operations`** skill (ask Kiro: *"plan cutover for myproject"*) to
produce, under `migrations/myproject/04-operations/`:

- a **cutover runbook** (big-bang or minimal-downtime via AWS DMS change data capture),
- a **rollback plan**, and
- a **monitoring checklist** (pg_stat_statements, replication/CDC lag, Performance Insights).

Cutover execution is a high-risk production action — do it step by step under your own
direction, with verified backups before the point of no return.

---

## 9. Workspace artifacts

Everything a run produces lives under `migrations/<project>/` (git-ignored):

```
migrations/myproject/
├── 01-assessment/
│   ├── inventory-<SCHEMA>.yaml / .json      # object counts, tables, datatypes, code units
│   └── preflight.md                        # (written by the inception skill)
├── 02-construction/
│   ├── prompts/APP/*.prompt.md             # conversion prompt bundles (Kiro reads these)
│   ├── ddl/app/*.sql                       # converted PostgreSQL DDL (Kiro writes these)
│   ├── manifest.yaml                       # per-unit status: pending/converted/applied/failed
│   ├── apply_report.yaml                   # apply results
│   ├── code_prompts/ , code/ , code-manifest.yaml   # PL/SQL code pass
│   └── conversion-log.md                   # (decisions, playbook refs — traceability)
├── data/
│   ├── migrate_report.yaml                 # rows copied per table
│   └── _state/*.json                       # resume watermarks
├── 03-validation/
│   ├── reconcile_report.yaml               # row-count reconciliation
│   ├── test_prompts/APP/*.prompt.md        # test-gen prompts (Kiro reads these)
│   ├── tests/APP/*.test.yaml               # test specs (Kiro writes these)
│   ├── test-manifest.yaml                  # per-object test status
│   └── equivalence-report.yaml / .md       # function/procedure test results
├── follow-up.yaml / follow-up.md           # logged failures to resolve later (silent mode)
└── 04-operations/                          # cutover runbook, rollback, monitoring
```

---

## 10. Command reference

| Command | Purpose | Key options |
|---|---|---|
| `test-connection` | Verify source/target connectivity | `--side source\|target\|both` |
| `inventory` | Assess a source schema; write reports | `--schema`, `--project` |
| `convert-schema` | Extract object-units + build prompts (Kiro converts) | `--schema`, `--project`, `--tables` |
| `convert-code` | Extract PL/SQL code objects + build prompts | `--schema`, `--project` |
| `apply-schema` | Apply converted DDL (defers FK + triggers); auto error-retry loop (skips applied) | `--schema`, `--project`, `--code`, `--post-data`, `--tables`, `--max-retries`, `--mode`, `--dry-run` (print the DDL without executing) |
| `migrate-data` | Parallel data copy (COPY + resume) | `--schema`, `--workers`, `--batch-size`, `--tables`, `--exclude`, `--truncate` |
| `gen-tests` | Sample real data + build test-gen prompts (Kiro writes specs) | `--schema`, `--project`, `--mode` |
| `run-tests` | Run equivalence tests (txn+rollback); function/procedure parity | `--schema`, `--project`, `--mode` |
| `compare` | Reconcile source vs target row counts | `--schema`, `--project`, `--tables`, `--mode` |
| `mark` | Set manifest unit statuses (helper for the Kiro conversion loop) | `--schema`, `--project`, `--status`, `--code`/`--tests`, `--tables`, `--only-existing-output` |

Common environment variables:

| Var | Default | Meaning |
|---|---|---|
| `CONN_FILE` | `./connections.yaml` | connections file path |
| `MIGRATION_CONFIG` | `./migration-config.yaml` | migration config path |
| `DBMIG_MIGRATIONS_DIR` | `<repo>/migrations` | per-run workspace root — point outside the repo for isolated, easily-cleaned-up test runs |
| `DBMIG_CONNECT_TIMEOUT` | `30` | connection establishment timeout (seconds) |
| `DBMIG_MODE` | unset | failure handling: `silent` or `interactive` (overrides config) |
| `NO_COLOR` | unset | disable colored output |

---

## 11. Troubleshooting

- **`missing dependency: oracledb` / `psycopg`** → `pip install -r scripts/requirements.txt`.
- **`file not found: connections.yaml`** → run from the repo root, or set `CONN_FILE`.
- **Oracle connect fails** → check `service_name` vs `sid`, host/port reachability, and that
  env vars are exported.
- **PostgreSQL connect fails on SSL** → adjust `sslmode` (`require` for Aurora; `disable` for
  a local test DB).
- **`apply-schema` reports failures** → the retry loop handles most automatically: on
  `RETRY_AVAILABLE`, Kiro re-converts each failed unit from its `retries/<SCHEMA>/*.retry.md`
  and re-applies, up to `llm.max_retries`. Only on `MAX_RETRIES_EXHAUSTED` (units marked
  `needs_human`) do you step in — read each unit's `last_error` in the manifest and
  `apply_report.yaml`, then fix the `.sql`, add a `customer-specific/` override, or redesign.
- **Conversion produced wrong types** → add an override in `customer-specific/`, re-run
  `convert-schema`, have Kiro re-convert; customer-specific rules win.
- **`migrate-data` resumed unexpectedly / want a clean reload** → delete the table's file in
  `migrations/<project>/data/_state/` (and `--truncate`), then re-run.

---

## 12. Safety notes

- `connections.yaml`, `migration-config.yaml`, and `migrations/` are git-ignored; prefer
  `${ENV_VAR}` references over plaintext passwords.
- Applying DDL, loading data, and procedure parity tests **write to the target** — gated
  actions. Use a dedicated test schema/database; never run net-effect procedure tests
  against a populated production target.
- Production cutover/data movement is high-risk: confirm each irreversible step and verify
  backups first. Keep the source intact and reachable through a soak period.
- The playbook references are distilled from the AWS *Oracle to Aurora PostgreSQL Migration
  Playbook* and are reference only — **test everything in a non-production environment first.**
