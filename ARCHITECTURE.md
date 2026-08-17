# Architecture

This document explains how **dbmig-aidlc** is put together and why. It is written to be read
top-to-bottom: start with the big picture, then drill into each layer.

---

## 1. The core idea

A database migration is treated as an **AI-DLC lifecycle** — a sequence of phases with clear
inputs, outputs, and **human approval gates** — rather than a one-shot "convert my schema"
script. Two design decisions follow from that:

1. **The AI is an orchestrator, not a black box.** Kiro (the agent) runs an intake interview,
   moves through phases, and stops for human approval between them. Every phase writes
   durable artifacts so the work is inspectable and traceable.

2. **Determinism and intelligence are separated.** Anything mechanical (connect, extract DDL,
   apply DDL, copy data, reconcile, run tests) is done by a plain **Python package** that
   runs standalone. The genuinely intelligent step — **schema/code conversion** — is done by
   **Kiro itself**, using distilled AWS playbook knowledge as context. The Python package
   makes **no LLM API calls**.

```
                    ┌─────────────────────────────────────────────┐
                    │                  Kiro (agent)               │
                    │   orchestrator + phase skills + conversion  │   ← intelligence
                    └───────────────┬─────────────────────────────┘
                                    │ runs commands / reads+writes artifacts
                                    ▼
                    ┌─────────────────────────────────────────────┐
                    │            dbmig Python package             │   ← determinism
                    │  connect · inventory · extract · apply ·    │
                    │  migrate-data · compare · gen/run tests     │
                    └───────────────┬─────────────────────────────┘
                                    │ Python DB drivers (no native client tools)
                          ┌─────────┴─────────┐
                          ▼                   ▼
                    Source DB             Target DB
               (Oracle / SQL Server)   (PostgreSQL / MySQL)
```

---

## 2. The two layers

### 2.1 The skill layer (the "brain") — `skills/`

Each phase is a Kiro **skill** (a `SKILL.md` with instructions). They are engine-agnostic and
read the active engine pair's definition at run time.

| Skill | Role |
|---|---|
| `db-migration-orchestrator` | **Entry point.** Intake interview, connectivity pre-flight, routes between phases, enforces the approval gates. |
| `db-migration-inception` | Assessment & planning: inventory, compatibility classification, migration plan. |
| `db-migration-construction` | **Conversion.** Kiro converts each object-unit/code object from the prompt bundles, then applies them (with the error-retry loop). |
| `db-migration-validation` | Data load (or AWS DMS hand-off), reconciliation, and LLM-generated equivalence testing. |
| `db-migration-operations` | Cutover runbook, rollback plan, monitoring. |
| `<pair>-playbook` (×4) | **Knowledge base.** AWS migration playbooks distilled into granular per-topic references the converter consults. |
| `app-modernization-*` (×5) | **Optional module** (orchestrator + Inception/Construction/Validation/Operations): conforms *application code* to a completed migration. Opt-in only; never auto-starts. |

### 2.2 The toolkit layer (the "hands") — `scripts/dbmig/`

A pure-Python package invoked as `python -m dbmig <command>`. It owns every deterministic
operation and connects with **pure-Python drivers** (no `sqlplus`/`psql`/`sqlcmd` install):
`oracledb` (thin), `python-tds`, `psycopg` v3, `PyMySQL`.

```
scripts/dbmig/
├── cli.py            # argparse; dispatches subcommands
├── config.py         # load + ${ENV} expand configs; active_pair(); LLM/run settings
├── connections.py    # Connection dataclass + db_connect() per engine
├── console.py        # colored output + live progress
├── followup.py       # run modes (silent/interactive) + follow-up log
├── engines/          # the engine ADAPTER layer (see §5)
│   ├── base.py       #   SourceEngine / TargetEngine ABCs + ObjectUnit/CodeObject
│   ├── registry.py   #   engine name -> adapter class
│   ├── oracle.py · sqlserver.py        # source adapters
│   ├── postgresql.py · mysql.py        # target adapters
│   └── _common.py    #   shared multi-pass apply
├── conversion/       # the LLM hand-off
│   ├── prompt_builder.py   # assemble pair-aware prompt bundles
│   ├── output_parser.py    # extract executable DDL from Kiro's answer
│   └── llm_client.py       # provider=kiro (hand-off; no API)
└── commands/         # one module per subcommand (use adapters only)
```

---

## 3. The lifecycle (four phases)

```
 Inception ──gate──► Construction ──gate──► Validation ──gate──► Operations
 (assess)            (convert+apply)        (load+test)          (cutover)
```

Each phase is human-gated: the orchestrator presents the artifacts and waits for approval
before advancing. Per phase, the split between deterministic work and Kiro intelligence:

| Phase | Deterministic (dbmig) | Intelligent (Kiro) |
|---|---|---|
| Inception | `inventory` (object counts, tables, datatypes, code units) | compatibility assessment, migration plan |
| Construction | `convert-schema`/`convert-code` (extract + build prompts), `apply-schema` (multi-pass apply) | **convert each object-unit/code object to target DDL** |
| Validation | `migrate-data` (or DMS), `compare`, `gen-tests` (sample real data), `run-tests` (execute + diff) | **generate equivalence test specs from real data** |
| Operations | — | cutover runbook, rollback plan, monitoring checklist |

---

## 4. The conversion hand-off (how Kiro is "called")

There is **no programmatic LLM call**. Conversion is a **file-based hand-off** where Kiro is
the executor:

```
dbmig convert-schema                          Kiro (construction skill)
──────────────────────────                    ─────────────────────────
1. extract object-units (adapter)
2. build prompt bundles  ───────────────►  3. read each prompt bundle
   02-construction/prompts/<S>/*.md            (context + source DDL baked in)
3. write manifest.yaml (status: pending)    4. produce target DDL
                                            5. write ddl/<s>/<table>.sql
                                            6. set status: converted
                                                   │
dbmig apply-schema  ◄──────────────────────────────┘
7. apply DDL to target (multi-pass)
```

The "interface" between the two is just files on disk: **prompt bundles** (input to Kiro) and
the **manifest** (work queue + per-unit status). `conversion/llm_client.py` ships only the
`kiro` provider, whose `convert()` raises `HandoffRequired` — it never generates DDL itself.
The seam is forward-compatible: a hosted-LLM client could be added to run the loop unattended,
but that is deliberately not built (the LLM is Kiro).

**Object-units, not layers.** Extraction groups each table with its indexes, constraints
(PK/UK/FK/CHECK), DML triggers, comments and grants into one `ObjectUnit`. Converting the unit
as a whole lets Kiro make holistic decisions (e.g. choose an index type given a constraint).
PL/SQL / T-SQL code objects are a **separate pass** (`convert-code`) because they need
different context.

**Error-retry loop.** `apply-schema` is status-aware (skips already-applied units) and
multi-pass (resolves FK ordering). When a unit fails, it writes a **remediation prompt** (the
original prompt + the failed DDL + the exact database error) and prints `RETRY_AVAILABLE`;
Kiro re-converts and re-applies, up to `llm.max_retries`. Units that exhaust the budget are
marked `needs_human` (`MAX_RETRIES_EXHAUSTED`).

---

## 5. The engine adapter pattern (multi-pair support)

This is what lets one codebase serve many engine pairs **without per-pair scripts**.

```
                         ┌──────────────┐        ┌──────────────┐
                         │ SourceEngine │        │ TargetEngine │   (ABCs in base.py)
                         │   (ABC)      │        │   (ABC)      │
                         └──────┬───────┘        └──────┬───────┘
              ┌─────────────────┴───────┐         ┌─────┴─────────────────┐
              ▼                         ▼         ▼                       ▼
        OracleEngine            SQLServerEngine   PostgreSQLEngine    MySQLEngine
        (oracle.py)             (sqlserver.py)    (postgresql.py)     (mysql.py)
```

- **`SourceEngine`** (read side): `connect`, `ping_sql`, `extract_object_unit_ddl`,
  `extract_code_objects`, `get_table_list`, `chunk_iterator`, `inventory`, `count_rows`, …
- **`TargetEngine`** (write side): `connect`, `ping_sql`, `apply_ddl`, `apply_units`
  (multi-pass), `bulk_insert` (COPY for PostgreSQL, batched INSERT for MySQL),
  `get_row_count`, `ensure_schema`, …
- **`registry.py`** maps an engine name (with aliases like `aurora-mysql`→`mysql`) to its
  adapter class and enforces role (a target engine can't be used as a source).

**All commands depend only on the adapter interface**, resolved via
`get_source_engine(pair)` / `get_target_engine(pair)` — never on engine-specific code. The
active pair is derived from the connection engines: `oracle` + `postgresql` →
`oracle-to-postgresql`.

A migration **pair is a composition** of one source adapter and one target adapter plus
context material:

```
oracle-to-postgresql   = OracleEngine     + PostgreSQLEngine + engines/oracle-to-postgresql/   + skills/oracle-to-postgresql-playbook/
oracle-to-mysql        = OracleEngine     + MySQLEngine      + engines/oracle-to-mysql/        + skills/oracle-to-mysql-playbook/
sqlserver-to-postgresql= SQLServerEngine  + PostgreSQLEngine + engines/sqlserver-to-postgresql/+ skills/sqlserver-to-postgresql-playbook/
sqlserver-to-mysql     = SQLServerEngine  + MySQLEngine      + engines/sqlserver-to-mysql/     + skills/sqlserver-to-mysql-playbook/
```

> Two source adapters × two target adapters yield four pairs. `sqlserver-to-mysql` required
> **no new Python** — it reused the existing SQL Server source and MySQL target adapters.

**Source-DDL note.** Oracle exposes `DBMS_METADATA`; SQL Server does not, so `SQLServerEngine`
**reconstructs** each object-unit's DDL from `INFORMATION_SCHEMA` + `sys.*` catalogs. Both
present the same `ObjectUnit` shape to the rest of the system.

---

## 6. Conversion knowledge as context (not rules)

The converter's knowledge lives in data, not code:

- **`engines/<pair>/datatype-map.yaml`** — source→target type mappings and gotchas.
- **`skills/<pair>-playbook/references/`** — the AWS migration playbook distilled into
  granular per-topic files (Oracle/SQL-Server construct → target equivalent → workaround),
  each tagged with a **conversion category** (Automatic / Assisted / Manual / Blocked).
- **`skills/<pair>-playbook/references/customer-specific/`** — this customer's own rules
  (conventions, datatype overrides, forbidden patterns).

`conversion/prompt_builder.py` assembles a prompt per object-unit by injecting, in order:

```
1. CUSTOMER-SPECIFIC KNOWLEDGE   (HIGHEST PRECEDENCE — overrides everything below)
2. construction skill guidance
3. the pair's datatype map
4. the pair's playbook chapter indexes (what to consult)
5. the source object-unit DDL to convert
```

It is **source- and target-aware**: the instruction and the `SOURCE DDL (<engine>)` header
reflect the active pair (e.g. "Convert the following SQL Server object unit to MySQL DDL").

---

## 7. Data flow and artifacts (traceability)

Every run writes to a per-project workspace (git-ignored). This is the audit trail that ties
converted objects back to the original intent — the AI-DLC traceability principle.

```
migrations/<project>/
├── 01-assessment/    inventory-<SCHEMA>.yaml/json, migration-plan.md
├── 02-construction/  prompts/ · ddl/ · manifest.yaml · apply_report.yaml · retries/
│                     code_prompts/ · code/ · code-manifest.yaml
├── data/             migrate_report.yaml · _state/ (resume watermarks)
├── 03-validation/    reconcile_report.yaml · test_prompts/ · tests/ · equivalence-report.yaml
├── 04-operations/    cutover-runbook.md · rollback-plan.md · monitoring.md
└── follow-up.yaml    logged conversion/test failures awaiting human follow-up
```

**Data movement.** `migrate-data` runs one worker per table (ThreadPool); each worker pulls
PK-ordered chunks from the source adapter's `chunk_iterator` and ingests via the target
adapter's `bulk_insert` (PostgreSQL COPY / MySQL batched INSERT). **Resume** is guarded by a
signature over the ordered chunk boundaries: a matching signature lets committed chunks be
skipped safely, while boundary drift (source mutated or `--batch-size` changed) triggers a
truncate-and-reload instead of skipping wrong ranges; progress is written atomically
(temp file + `os.replace`). Before copying, a source→target column-alignment check fails loudly
on a mismatch. Types whose wire form is opaque to a generic COPY (SQL Server `hierarchyid` →
`.ToString()`, `geography`/`geometry` → `.STAsText()`) are converted to portable text at read
time. `--tables`/`--exclude` scope the set. It is for dev/test loads; production-scale movement
hands off to **AWS DMS**.

**Equivalence testing.** `gen-tests` samples **real** source rows and asks Kiro to write test
specs (`.test.yaml`); `run-tests` executes each case on both engines **inside a transaction
that is rolled back** — functions compared by return value, procedures by before/after
net-effect deltas. Procedures that manage their own transaction (COMMIT/ROLLBACK/BEGIN TRAN)
are flagged `test_mode: manual` — they can't be net-effect tested through the rollback harness.

---

## 8. Run modes and failure handling

Controlled by `run.mode` in `migration-config.yaml` (or `--mode` / `DBMIG_MODE`):

- **`silent`** (default) — any conversion or test failure is appended to
  `migrations/<project>/follow-up.yaml` and the run **continues**. Humans triage later.
- **`interactive`** — additionally prompts for input/correction and surfaces failures via a
  non-zero exit.

This keeps long migrations moving instead of halting on the first problem, while preserving a
complete to-do list of everything that needs human attention.

---

## 9. Extending the framework

**Add an engine pair that reuses existing adapters** (e.g. a new source/target combination):
add `engines/<pair>/` (datatype map + checks), `skills/<pair>-playbook/`, a guide, and you're
done — the pair resolves automatically.

**Add a brand-new engine:**
1. Implement `SourceEngine` and/or `TargetEngine` in `scripts/dbmig/engines/<engine>.py`.
2. Register it in `engines/registry.py` (`ENGINES`).
3. Add the `engines/<pair>/` definition + `skills/<pair>-playbook/` knowledge base + a guide.

In both cases there are **zero changes** to the CLI, prompt builder, data migration, or
reconciliation code — they all operate through the adapter interface.

---

## 9a. The optional application-modernization module

A database migration leaves the *application* speaking the old dialect. A separate, **opt-in**
module (`app-modernization-orchestrator` + one skill per AI-DLC phase) conforms application
code to a completed migration: embedded SQL, datasource/ORM configuration, entity mappings,
stored-routine call sites, error codes, result-set typing.

Design points, mirroring the DB side:

- **Contract-driven, not generic.** Inception derives an *app contract* from the migration's own
  artifacts (conversion log, code manifest, validation carry-forwards) — the app is conformed to
  what *this* migration did, not to a dialect pair in the abstract.
- **Gate before any edit.** Inception produces a per-site change plan (current vs proposed,
  mechanical vs behavioural, risk); nothing is edited until it is approved.
- **Mirrored backups.** Originals are copied to
  `migrations/<project>/05-application/backup/<timestamp>/<relative-path>` — never `.bak` files
  beside the sources.
- **Per-pair seam.** Application rules live in `engines/<pair>/app/` (`app-config.yaml` +
  `app-sql-rules.md`, one identical schema across pairs), so a new pair needs no skill changes.
  They are deliberately *not* under the playbook: the playbook's `references/*/_index.md` files
  are injected into DB-schema conversion prompts, where app rules would be noise.
- **Like-for-like only.** The app keeps its architecture and framework; this is not refactoring.

Proven on a Java/Spring Boot/JPA app (Oracle→PostgreSQL, Oracle→MySQL) and a .NET/EF Core app
(SQL Server→PostgreSQL, SQL Server→MySQL), each validated by live queries against the migrated
target.

## 10. Security & safety

- Connection and config files (`connections.yaml`, `migration-config.yaml`) and the
  `migrations/` workspace are git-ignored; secrets are referenced via `${ENV_VAR}`.
- Connectivity is via Python drivers with no native client tools; secret values are never
  echoed (the `Connection` repr masks the password).
- Writes to the target (DDL apply, data load, procedure tests) are **gated actions**;
  net-effect procedure tests run in a rolled-back transaction and should target a disposable
  database.
- Production cutover and data movement are high-risk: confirmed step by step, with backups
  verified before the point of no return.
