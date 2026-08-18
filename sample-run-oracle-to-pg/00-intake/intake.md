# Intake — DEMO (Oracle → Aurora PostgreSQL)

## Engine pair
- **Source:** Oracle 19c
- **Target:** PostgreSQL (Aurora PostgreSQL) 17.7
- **Active pair:** `oracle-to-postgresql`

## Connections (secrets from AWS Secrets Manager — profile `workshop`, `us-east-1`)
| Side | Host | Port | DB / SID | User | Secret |
|---|---|---|---|---|---|
| Source | oracle-source.example.com | 1521 | SID `ORCL` | admin | `oracle-admin-secret` |
| Target | aurora-cluster.example.com | 5432 | `demodb` | postgres | `aurora-admin-secret` |

Secrets injected via `${ENV_VAR}` from git-ignored `.env`; never stored in `connections.yaml`.

## Scope & strategy
- **Source schema:** `DEMO`
- **Target schema:** `demo` (in `demodb`)  — `default_schema: demo`, `identifier_case: lower_case`
- **Object types:** tables, indexes, constraints, sequences, views, functions, procedures, packages, triggers
- **Strategy:** `full` (schema + data)
- **Data volume:** `full` (complete data load via framework `migrate-data`)
- **Run mode:** silent (failures logged to `follow-up.yaml`)
- **Project workspace:** `migrations/demo/`

## Decisions / notes
- User directed **not** to reuse `sample-run-oracle-to-pg/` conversions — Kiro performs a fresh conversion.
- Oracle connection uses SID `ORCL` (from secret `dbname`); switch to `service_name` if connectivity fails.

## Phase gates
Inception → (gate) → Construction → (gate) → Validation → (gate) → Operations → (gate).
