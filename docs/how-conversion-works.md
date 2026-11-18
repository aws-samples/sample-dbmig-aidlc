# How conversion works — the LLM is Kiro

There is **no datatype rule engine**. The `dbmig` package does the deterministic work
(extract source object-units, build prompt bundles, apply DDL, copy data, reconcile) and
**Kiro performs the actual schema/code conversion** via the `db-migration-construction`
skill. The package makes **no LLM API calls** and runs standalone for every other step.

Conversion works on **object-units** — a table together with its indexes, constraints
(PK/UK/FK/CHECK), DML triggers, comments and grants — so the conversion is holistic rather
than layer-by-layer. The active pair's `engines/<source>-to-<target>/` directory (datatype
map) and the matching `<pair>-playbook` references are injected into the prompt as **context
material**, not executed as rules. Customer-specific rules, questionnaire policies and answered
decisions come first in that context, with the highest precedence.

## The full CLI pipeline

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

Each phase ends with `./dbmig gate status` / `gate approve <phase>`; see
[Gates, decisions and the review site](gates-and-review.md).

## Failures, follow-ups and retries

- When a unit fails to apply, `apply-schema` writes a remediation prompt with the target
  database's error and Kiro re-converts it, up to `llm.max_retries` (default 3). A unit still
  failing becomes `needs_human` and raises a decision.
- Conversion or test failures are, by default (silent mode), logged to
  `migrations/<project>/follow-up.yaml` and the run continues; use `--mode interactive` to be
  prompted instead. When a re-run of `run-tests` / `compare` / `apply-schema` passes, the matching
  follow-up items are set to `resolved` automatically.
- `gen-tests` tags objects whose source tables are all empty as `LOW_COVERAGE`, and `run-tests`
  reports them separately.

For production-scale data movement use AWS DMS (the framework hands off to it); the built-in
`migrate-data` is for dev/test loads and reconciliation.

The per-pair [guides](../guides/README.md) walk through each step in detail, and
[ARCHITECTURE.md](../ARCHITECTURE.md) describes the design.
