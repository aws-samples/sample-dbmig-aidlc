# Run workspaces and multiple runs

Each run's artifacts (inventory, prompts, converted DDL/code, reports, data state, gate records)
live under a **per-run workspace**: `migrations/<project>/`. Two settings control where a run is
written, so you can keep runs isolated and re-run without overwriting a previous one:

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

## Workspace layout

```
migrations/<project>/
├── project.yaml        # gate records, decisions, questionnaire policies
├── 00-intake/          # intake.md; questionnaire.md (questionnaire mode)
├── 01-assessment/      # inventory, compatibility assessment, migration plan (DMS SC: triage, diff, VERIFY ledger)
├── 02-construction/    # prompts, converted DDL + stored code, manifests, apply/retry reports, conversion log
├── data/               # data-migration reports + resume watermarks
├── 03-validation/      # reconcile + equivalence test reports, test specs
├── 04-operations/      # cutover runbook, rollback plan, monitoring, identity reset
├── 05-application/     # optional application modernization
├── review/             # generated review site (./dbmig review)
├── SIGN-OFF.md         # generated from the gate records
├── migration-report.md # phase-aligned summary (DMS SC path)
└── follow-up.yaml      # logged conversion/test failures (silent mode)
```

`migrations/` is git-ignored: it holds your DDL, code and sample data.
