# Cutover Runbook — DEMO (Oracle 19c → Aurora PostgreSQL 17.7)

**Target:** `demodb` / schema `demo` on `aurora-cluster.example.com:5432` (Aurora PostgreSQL 17.7)
**Source:** Oracle 19c, SID `ORCL`, schema `DEMO` on `oracle-source.example.com:1521`
**Scope:** 14 tables / 199 rows, 12 identity sequences, 16 FKs, 1 trigger, 1 GIN full-text index,
18 functions, 10 procedures.

---

## Strategy decision: big-bang with a short maintenance window

| Option | Fit here | Verdict |
|---|---|---|
| **Big-bang (downtime)** | The entire dataset is **199 rows**; a full reload takes seconds. Reconciliation and 103 equivalence tests already pass against a full copy. | **RECOMMENDED** |
| **Minimal-downtime (AWS DMS CDC)** | Adds a replication instance, CDC task, supplemental logging on Oracle, and lag monitoring — all to avoid a window measured in **minutes** on a 199-row database. | Not warranted |

> **If this runbook is reused for a production-scale schema**, switch to DMS: bulk load + CDC,
> cut over when lag ≈ 0. `dbmig migrate-data` is explicitly a dev/test loader and must not be
> used for large production data movement.
> Ref: `skills/oracle-to-postgresql-playbook/references/tools/aws-dms.md`

**Estimated total window: ~35–50 minutes**, dominated by verification rather than data movement.

---

## Roles
| Role | Responsibility |
|---|---|
| **Migration lead (ML)** | Runs the runbook, owns the go/no-go call |
| **DBA** | Snapshots, Oracle freeze, target DDL/data operations |
| **App owner (APP)** | Connection-string/driver switch, app deploy, app smoke checks |
| **QA** | Business smoke tests, sign-off |

---

## Phase 0 — Pre-cutover (T-2 days → T-1 hour, no downtime)

| # | Step | Owner | Est. | Rollback trigger |
|---|---|---|---|---|
| 0.1 | Confirm the app build carrying the 4 carry-forward changes is ready and tested against `demodb` (see "Application changes" below). **The app will not work without these.** | APP | — | App build not ready → **postpone** |
| 0.2 | Re-run the equivalence suite to confirm no drift: `python -m dbmig run-tests --schema DEMO --project demo` → expect **103/103**. | ML | 5 min | Any failure → postpone |
| 0.3 | Schema diff — confirm the target still matches the approved conversion: run `04-operations/smoke-test.sql` checks 1 and 3. | DBA | 5 min | Object count mismatch → investigate, postpone |
| 0.4 | Verify target capacity/params: instance class, `max_connections` ≥ app pool + headroom, storage autoscaling on, Performance Insights enabled, `pg_stat_statements` loaded. | DBA | 15 min | — |
| 0.5 | Confirm the app DB user exists on the target with least privilege (`CONNECT`, `USAGE` on `demo`, table DML, `EXECUTE` on routines) — **do not ship the `postgres` superuser to the app**. | DBA | 10 min | — |
| 0.6 | Verify backups: an **Aurora snapshot** of `demodb` and a **current Oracle backup/RMAN or snapshot**. Record both snapshot IDs here. | DBA | 15 min | **No verified backup → STOP. Do not proceed.** |
| 0.7 | Announce the window; freeze schema/code changes on both sides. | ML | — | — |

---

## Phase 1 — Quiesce the source (T+0, downtime starts)

| # | Step | Owner | Est. | Rollback trigger |
|---|---|---|---|---|
| 1.1 | Stop application traffic (drain the LB / scale app to 0 / enable maintenance page). | APP | 5 min | — |
| 1.2 | Confirm no active sessions on Oracle: `SELECT username, status, count(*) FROM v$session WHERE username='DEMO' GROUP BY username, status;` | DBA | 2 min | Sessions persist → kill or abort |
| 1.3 | Make the source **read-only** so nothing can write behind you: `ALTER USER DEMO ACCOUNT LOCK;` (or revoke DML). Keeps the source intact for rollback. | DBA | 2 min | — |
| 1.4 | Capture the authoritative source counts (the rollback/verification baseline): per-table `COUNT(*)`, total **199**, and `SELECT SUM(quantity) FROM DEMO.LISTINGS` (expect **396**). Record them. | DBA | 3 min | — |

**Point of no return has NOT been reached.** Everything so far is reversible by unlocking the
Oracle account and restoring traffic.

---

## Phase 2 — Final data sync

| # | Step | Owner | Est. | Rollback trigger |
|---|---|---|---|---|
| 2.1 | Reload data into the (already-converted) target. Because the schema and code are applied and validated, only data needs refreshing:<br>`python -m dbmig migrate-data --schema DEMO --workers 8 --project demo`<br>The loader truncates and re-copies in FK-dependency order, then advances the identity sequences. | DBA | 5 min | Any table fails to load → **roll back (Phase R)** |
| 2.2 | Confirm the deferred FKs and the trigger are in place (already applied; idempotent): `python -m dbmig apply-schema --schema DEMO --project demo --post-data` | DBA | 2 min | Failure → roll back |
| 2.3 | Reconcile: `python -m dbmig compare --schema DEMO --project demo` → expect **14/14 match**, totalling the 199 rows recorded in 1.4. | DBA | 3 min | Any mismatch → **roll back** |
| 2.4 | **Verify identity sequences are ahead of `MAX(id)`** (smoke-test check 3). If skipped, the first application insert will raise a duplicate-key error. | DBA | 2 min | Any sequence behind → fix with `setval`, re-verify |

---

## Phase 3 — Switch the application

| # | Step | Owner | Est. | Rollback trigger |
|---|---|---|---|---|
| 3.1 | Deploy the app build from 0.1 pointing at the target. JDBC URL becomes `jdbc:postgresql://aurora-cluster.example.com:5432/demodb?currentSchema=demo&ssl=true&sslmode=require` (driver `org.postgresql.Driver`). Credentials from Secrets Manager `aurora-admin-secret` — or, preferably, a dedicated least-privilege app secret. | APP | 10 min | Deploy failure → roll back |
| 3.2 | Confirm the app connects and its pool is healthy; check `pg_stat_activity` shows the expected session count. | APP/DBA | 5 min | Cannot connect → roll back |

---

## Phase 4 — Verify before opening traffic

| # | Step | Owner | Est. | Rollback trigger |
|---|---|---|---|---|
| 4.1 | Run the technical smoke test **as the app user**: `psql -h aurora-cluster.example.com -U <app_user> -d demodb -v ON_ERROR_STOP=1 -f 04-operations/smoke-test.sql`. It asserts object counts, row counts, identity sequences, GIN full-text search **and that the index is used**, the search trigger, business routines, and the `U0002` error contract. It raises on any failure. | DBA | 5 min | **Any failure → roll back** |
| 4.2 | QA business smoke: log in, **search for a book** (proves the Oracle Text → GIN redesign end-to-end), open a book detail page with its cover image (proves BLOB → `bytea`), add to cart, place an order (proves identity inserts + `order_pkg`), view order history. | QA | 15 min | Functional failure → roll back |
| 4.3 | **Go/no-go decision.** | ML | 5 min | No-go → roll back |

---

## Phase 5 — Open to traffic and monitor

| # | Step | Owner | Est. |
|---|---|---|---|
| 5.1 | Restore traffic (remove maintenance page / scale app up). Downtime ends. | APP | 5 min |
| 5.2 | Begin the monitoring schedule in `monitoring.md` — first 60 minutes at high attention. | ML/DBA | ongoing |
| 5.3 | Run `ANALYZE demo.<each table>;` (or `VACUUM ANALYZE`) so the planner has fresh statistics after the bulk load. | DBA | 5 min |
| 5.4 | Keep Oracle **locked but intact** for the soak period (see `rollback-plan.md`). Do not decommission. | DBA | — |

---

## Point of no return

**The point of no return is when the application begins accepting production writes on Aurora
(step 5.1).** Before that, rollback is a clean connection-string revert. After it, any writes
that land on Aurora exist only there, and rolling back means reconciling that divergence — see
`rollback-plan.md` §3.

---

## Application changes required (from validation — the app will misbehave without these)

1. **Full-text search predicates** — `CONTAINS(search_text, :q) > 0` becomes
   `to_tsvector('english', coalesce(search_text,'')) @@ to_tsquery('english', :q)`.
   Note English stopwords (e.g. `the`) do not match.
2. **Error codes** — catch SQLSTATE **`U0001`** (insufficient inventory) and **`U0002`**
   (invalid action) instead of `ORA-20001` / `ORA-20002`.
3. **Transactions** — `archive_old_orders`, `clear_shopping_cart`, `process_customer_offer` and
   `set_book_featured` **no longer `COMMIT`**. The caller must commit.
4. **Package calls flattened** — `ORDER_PKG.CREATE_ORDER(...)` becomes
   `demo.order_pkg_create_order(...)`; same pattern for `book_pkg_`, `inventory_pkg_`,
   `reporting_pkg_`, `validation_pkg_`.

Also note `PERSISTENT_LOGINS` was an Index-Organized Table and is now a heap table with a
primary key — functionally identical, physical clustering not preserved.
