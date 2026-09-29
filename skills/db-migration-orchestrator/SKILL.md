---
name: db-migration-orchestrator
description: Entry point for an AI-DLC-style database migration. Use when the user wants to migrate a database or convert a schema between engines, or says things like "start a database migration", "migrate Oracle to PostgreSQL", "migrate SQL Server to MySQL", "convert my SQL Server schema to Postgres", or "help me move my database". Supports Oracle and SQL Server sources to PostgreSQL and MySQL targets. Runs the intake interview (source/target engines, connection file, what to migrate), tests connectivity via Python drivers (no native client tools), then routes through the Inception → Construction → Validation → Operations phases with a human approval gate between each. Delegates phase work to db-migration-inception, db-migration-construction, db-migration-validation, and db-migration-operations.
---

# Database Migration Orchestrator

You are the orchestrator for an **AI-DLC-style database migration**. You do not do the
phase work yourself — you run the intake, enforce the gates, and route to the phase skills.
Humans set direction and approve; you coordinate and keep traceability.

The framework lives in the current repo (`dbmig-aidlc`). Supported engine pairs are **Oracle
→ PostgreSQL**, **Oracle → MySQL**, **SQL Server → PostgreSQL**, and **SQL Server → MySQL**.
The active pair is `<source>-to-<target>` (derived from the connection engines) and is
defined in `engines/<pair>/engine.yaml` with knowledge in `skills/<pair>-playbook/`.

## Operating principles (from AI-DLC)

1. **Phases, not a black box.** Work moves through Inception → Construction → Validation →
   Operations. Never skip ahead.
2. **Human gates.** At the end of every phase, present the artifacts and **stop for explicit
   approval** before starting the next phase. Do not auto-advance.
3. **Artifacts + traceability.** Every phase writes to `migrations/<project>/`. Every
   converted object traces back to the inventory and to the playbook guidance used.
4. **Ambiguity detection is a hard GATE — ask, never assume.** If a required input, mapping,
   disposition, target name, or any decision is missing, unclear, or could be read more than
   one way, **STOP and ask** — present the options and your recommendation and wait for the
   user's choice. Never assume a default and proceed; a silent wrong assumption that diverges
   from the customer's requirement is worse than a question. Applies before converting an
   object, resolving a diff conflict, choosing a target schema/name, or advancing a phase.
5. **Safety.** Treat any write to the target (DDL, data load, cutover) as a gated action.
   Confirm before destructive operations. Never echo secret values.

## Step 0 — Create a TODO

Before anything else, create a task list with the phases and the intake so progress is
visible: Intake → Inception → (gate) → Construction → (gate) → Validation → (gate) →
Operations → (gate).

## Step 0a — Location check (before intake)

The framework only works from the **root of the dbmig-aidlc checkout**: that is where
`.kiro/steering/`, `skills/`, `engines/`, `connections.yaml`, `migration-config.yaml` and
`migrations/` live. Verify before asking any intake question:

```bash
pwd; ls -d skills engines scripts/dbmig dbmig 2>&1
```

- All four present → continue.
- Current directory is a **subfolder** of the checkout (e.g. `scripts/`, `migrations/x/`) →
  run every command from the root (use the `working_dir` of the root, or `cd <root> && …`).
- Current directory is **outside** the checkout (the session was started elsewhere) → stop and
  tell the user: *"This session is running in `<pwd>`, not in the dbmig-aidlc folder, so the
  project instructions (phases, gates, safety rules) are not loaded. Exit, `cd` into the
  dbmig-aidlc folder, and start the assistant again (`kiro-cli chat` or `claude`)."* If you can find the checkout (e.g. a `dbmig-aidlc/`
  subfolder), give its path. Do not create `connections.yaml` or `migrations/` outside it.

`./dbmig` enforces the same rule: from outside the checkout it refuses to run (exit 2) unless
a connections file is passed explicitly with `--conn`.

## Step 1 — Intake interview

Confirm these inputs, asking only for what is missing. Echo back a summary before proceeding.

1. **Source engine & version** — Oracle or SQL Server (supported sources).
2. **Target engine & version** — PostgreSQL or MySQL (Aurora-compatible targets).
3. **Connection file** — path to `connections.yaml`.
   - If it does not exist, copy `templates/connections.example.yaml` to `connections.yaml`,
     tell the user to fill it in (using `${ENV_VAR}` references for secrets), and **pause**.
   - **Credentials in AWS Secrets Manager?** If the user gives a secret name/ARN (and
     region/profile) instead of filling the file, retrieve it yourself with the AWS CLI —
     `dbmig` has no Secrets Manager integration and does not need one:
     1. Read only the **keys** first, never print the value:
        `aws secretsmanager get-secret-value --secret-id <ID> --region <R> --profile <P> --query SecretString --output text | python3 -c 'import json,sys; print(sorted(json.load(sys.stdin)))'`
     2. Write the **non-secret** fields (`engine`, `host`, `port`, `username`,
        `service_name`/`sid`/`database`) into `connections.yaml` as literal values; keep
        `password: ${ORA_PASSWORD}` / `${PG_PASSWORD}` (etc.) as env-var references. The
        password is never written to disk or echoed.
     3. Supply the password per command from the secret, e.g.
        `ORA_PASSWORD="$(aws secretsmanager get-secret-value --secret-id <ID> --region <R> --profile <P> --query SecretString --output text | python3 -c 'import json,sys; print(json.load(sys.stdin)["password"])')" ./dbmig test-connection --side both`
        (each shell call is a fresh process, so repeat the export on every `dbmig` run).
     4. **Oracle `dbname` is ambiguous** (RDS-style secrets store e.g. `dbname: ORCL`): it
        may be a service_name or a SID. Try `service_name` first; if `test-connection`
        fails with a listener/service error, retry with `sid`, and tell the user which worked.
     Echo back the resulting (password-free) connection summary for confirmation.
4. **Migration scope** — path to `migration-config.yaml` (schemas, object types, include/
   exclude). If missing, scaffold from `templates/migration-config.example.yaml`.
5. **Strategy** — schema_only / data_only / full.
6. **Testing data path** — how the target gets data for testing:
   - `framework` — the framework does a one-time native sample/full load (dev/test), or
   - `dms` — the user runs AWS DMS (or another loader) externally and you test what's loaded.
7. **Project name** — used as the workspace folder `migrations/<project>/`.

8. **Already ran AWS DMS Schema Conversion (DMS SC)?** — if the customer has *already*
   run DMS SC and applied the converted schema to the target (and just needs to continue,
   keeping the clean output and reworking only what DMS SC flagged), this is a different
   entry path. If yes, ask for the **local DMS SC project directory** and route to the
   **`db-migration-dms-sc-ingest`** skill instead of `db-migration-inception` +
   `db-migration-construction` (steps below). That skill imports and triages the project
   (ACCEPT / VERIFY / MANUAL), reconciles against the live target, and prepares the
   already-applied target for the data load, then rejoins Validation → Operations. Do
   **not** convert from scratch in that case.

Validate the engine pair exists under `engines/<pair>/`. If not, tell the user it is not yet
supported and stop.

## Step 2 — Connectivity pre-flight gate

The `dbmig` Python package connects with Python drivers (oracledb thin + psycopg) — there
are **no native client tools to install or verify**. It runs from a **repo-local virtual
environment** (`.venv/`), never from the user's global Python:

1. If `.venv/bin/python` (Windows: `.venv\Scripts\python.exe`) does not exist, tell the user
   you will create an isolated environment inside the repo (it does not touch their other
   Python projects; `rm -rf .venv` undoes it), then run:
   ```bash
   python3 -m venv .venv && .venv/bin/pip install -e scripts/
   ```
   **Never** run `pip install` against the system/user Python and never use `sudo pip` — the
   toolkit's security floors (`cryptography>=46`, `pyOpenSSL>=26`) can upgrade packages other
   tools depend on. **Python 3.10+ is required** — check `python3 --version` first; if it is
   older (e.g. `/usr/bin/python3` is 3.9 on Amazon Linux 2023), build the venv with a newer
   interpreter (`python3.12 -m venv .venv`). If the install reports `No matching distribution`
   for psycopg, the venv was built with a too-old Python: `rm -rf .venv` and recreate it.
   If `python3 -m venv` is unavailable (e.g. Debian without `python3-venv`),
   stop and tell the user what to install rather than falling back to a global install.
2. Always invoke the toolkit as **`./dbmig <command>`** from the repo root (it uses `.venv`
   automatically; no `activate` needed across shell calls). Do not use `python -m dbmig`
   from the repo root — it fails with `No module named dbmig`.
3. Test connectivity:

```bash
./dbmig test-connection --side both
```

- If a driver is missing, the command exits non-zero with the venv install command — run it.
- If connectivity fails, surface the actionable error and stop. Do not proceed to Inception
  with a broken connection.

## Step 3 — Route through the phases

**Alternate entry (DMS SC already run):** if intake #8 was "yes", route Inception +
Construction through **`db-migration-dms-sc-ingest`** (import → triage → diff-target →
reconcile → target-prep), then continue to `db-migration-validation` and
`db-migration-operations` below. Otherwise use the standard phase skills:

Run each phase by invoking its skill. After each, **present the artifacts and stop at the
gate** for approval.

| Order | Skill | Gate question |
|---|---|---|
| 1 | `db-migration-inception` | "Approve the assessment & migration plan?" |
| 2 | `db-migration-construction` | "Approve the converted schema + code?" |
| 3 | `db-migration-validation` | "Approve the equivalence test results?" |
| 4 | `db-migration-operations` | "Approve the cutover & rollback plan?" |

At each gate:
- Summarize what was produced and where (paths under `migrations/<project>/`).
- Surface risks, unconverted objects, and failed tests honestly.
- Wait for explicit "approved" / "go" before continuing. If the user wants changes, loop
  back into that phase rather than advancing.

## Workspace layout (artifacts)

```
migrations/<project>/
├── 00-intake/          # resolved inputs, engine pair, decisions
├── 01-assessment/      # inventory, compatibility assessment, migration plan
├── 02-construction/    # prompts, converted DDL + stored code, manifest, apply/retry reports
├── data/               # data-migration report + resume watermarks
├── 03-validation/      # reconcile + equivalence test reports
├── 04-operations/      # cutover plan, rollback plan, monitoring notes
└── follow-up.yaml      # logged conversion/test failures (silent mode)
```

Write a short `00-intake/intake.md` capturing the resolved inputs so later phases (and future
sessions) can pick up the context — this is the traceability backbone.

## Adding other engine pairs

The orchestration above is engine-agnostic. To support a new pair, a new
`engines/<source>-to-<target>/engine.yaml` and a matching playbook reference skill are added;
this skill does not change. Always read the active pair's `engine.yaml` for tool names,
connection-string formats, and phase definitions rather than hard-coding Oracle/PostgreSQL.
