# Rollback Plan — DEMO (Aurora PostgreSQL → back to Oracle)

Required by `migration-config.yaml` → `cutover.require_rollback_plan: true`.

**Core principle: Oracle remains the intact, authoritative fallback.** The migration never
drops, truncates, or alters source data — the source is only *locked* (read-only) at step 1.3
of the runbook. Rollback is therefore fast and low-risk, provided it happens before production
writes accumulate on Aurora.

---

## 1. Decision criteria — roll back if ANY of these is true

| # | Trigger | Detected at |
|---|---|---|
| R1 | A table fails to load, or reconciliation reports **any** row-count mismatch | Runbook 2.1 / 2.3 |
| R2 | An identity sequence cannot be advanced past `MAX(id)` (first insert would collide) | Runbook 2.4 |
| R3 | `smoke-test.sql` fails **any** of its 7 checks | Runbook 4.1 |
| R4 | Full-text search returns wrong results, or stops using `books_text_idx` | Runbook 4.1 / 4.2 |
| R5 | QA business smoke fails (login, search, cover image, cart, order placement) | Runbook 4.2 |
| R6 | The app cannot connect, or the connection pool is unstable | Runbook 3.2 |
| R7 | Post-cutover error rate exceeds the normal baseline, or p95 latency regresses badly and is not explained by cold caches/statistics | Monitoring, first 60 min |
| R8 | Data corruption or wrong values surface in production use | Any time in soak |
| R9 | The maintenance window will be exceeded with no credible path to green | ML judgement |

**Escalation:** the Migration Lead owns the call. R1–R6 are objective → roll back without debate.
R7–R9 require an ML judgement call; prefer rolling back and retrying over degraded service.

---

## 2. Rollback BEFORE the point of no return (no production writes on Aurora)

This is the expected case for R1–R6. **Estimated time: ~10 minutes.** No data reconciliation
needed, because Aurora holds no authoritative data.

| # | Step | Owner |
|---|---|---|
| 1 | Halt the cutover; announce rollback. | ML |
| 2 | Keep the app offline (maintenance page stays up). | APP |
| 3 | Unlock Oracle: `ALTER USER DEMO ACCOUNT UNLOCK;` (or restore the revoked DML grants). | DBA |
| 4 | Verify the source is untouched: per-table counts equal the Phase 1.4 baseline — total **199 rows**, `SUM(LISTINGS.QUANTITY)` = **396**. | DBA |
| 5 | Redeploy / re-point the app to the **Oracle** connection string (previous build, `oracle-admin-secret`). | APP |
| 6 | Run the app's pre-existing Oracle smoke checks. | QA |
| 7 | Restore traffic. Downtime ends, on Oracle. | APP |
| 8 | Leave the Aurora target as-is for post-mortem — **do not** drop `demo`; it is the evidence. | DBA |

---

## 3. Rollback AFTER production writes have landed on Aurora

Applies to R7–R9 once traffic is live (runbook 5.1+). Aurora now holds data Oracle does not, so
this is **no longer a clean revert** — it is a reconciliation exercise.

| # | Step | Owner |
|---|---|---|
| 1 | **Stop writes immediately** — maintenance page up. The longer writes continue, the larger the divergence. | APP |
| 2 | Take an **Aurora snapshot** to freeze the diverged state before touching anything. This is mandatory. | DBA |
| 3 | Quantify the divergence — the write-path tables are the ones to inspect:<br>`orders`, `order_items`, `shopping_cart_items`, `password_reset_tokens`, `persistent_logins`, plus `listings.quantity` (mutated by `inventory_pkg_reduce_inventory`), `listings.is_featured`/`status`/`processed_*` (mutated by `set_book_featured` / `process_customer_offer`), and `books.search_text` (trigger-maintained).<br>All of `orders`/`order_items`/`shopping_cart_items` were **empty at cutover**, so any row present is new and was created on Aurora. | DBA |
| 4 | Decide, with the business, per divergence: **(a)** replay the new rows into Oracle, **(b)** accept the loss and communicate it, or **(c)** roll *forward* by fixing the defect on Aurora instead. For a small volume, (a) is usually feasible: extract new rows and insert into Oracle, remembering Oracle identity columns will re-allocate unless values are supplied explicitly. | ML + business |
| 5 | If replaying: extract from Aurora, transform back (`bytea` → BLOB, `timestamp(0)` → DATE, `U000n` → app-level errors), load into Oracle, then re-verify counts and totals on both sides. | DBA |
| 6 | Unlock Oracle, re-point the app, smoke test, restore traffic. | DBA/APP/QA |

> Because `ORDERS`, `ORDER_ITEMS` and `SHOPPING_CART_ITEMS` are empty at cutover, divergence
> after a short soak is easy to isolate: every row in them is new. This is the single biggest
> factor keeping post-cutover rollback tractable here.

---

## 4. Soak period and decommissioning

| Milestone | Action |
|---|---|
| **T+0 → T+60 min** | High-attention monitoring (`monitoring.md`). Rollback per §2/§3 stays armed. |
| **T+24 h** | First checkpoint: no R7/R8 triggers → declare the cutover stable. |
| **T+7 days** | Soak complete. Oracle stays **locked but intact and reachable** for this entire period. |
| **After T+7 days, with written sign-off** | Only then consider decommissioning Oracle — and take a final **archival Oracle backup** first, retained per data-retention policy. |

**Do not** drop the Oracle `DEMO` schema, delete its backups, or release the host before the
soak completes and sign-off is recorded. Nothing in this migration requires deleting anything
on the source.

---

## 5. Recovery assets checklist (fill in during runbook step 0.6)

| Asset | Identifier | Verified by | When |
|---|---|---|---|
| Aurora pre-cutover snapshot | `______________________` | | |
| Aurora post-divergence snapshot (§3.2, only if rolling back late) | `______________________` | | |
| Oracle backup / RMAN / snapshot | `______________________` | | |
| Source baseline counts (199 rows; `LISTINGS` qty sum 396) | recorded at runbook 1.4 | | |
| Previous app build (Oracle-facing) | build/tag `______________` | | |

An empty row in this table at the point of no return is itself a **stop condition**.
