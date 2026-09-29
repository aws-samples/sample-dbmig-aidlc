# Run record — DEMO (Oracle 19c → Aurora PostgreSQL 17.7)

**Project:** `demo` · **Engine pair:** `oracle-to-postgresql` · connections masked (`sample_connections.yaml`).

This sample was produced as a **framework validation run**: the phases were executed end to end by the
assistant without a customer at the gates. The gate questions are listed for reference; in a real
migration each one is an explicit human approval.

| # | Phase | Gate question | This run |
|---|---|---|---|
| 1 | Inception | Approve the assessment & migration plan? | decision `fulltext_redesign` taken as option A (tsvector + GIN) — **requires owner sign-off** |
| 2 | Construction | Approve the converted schema + code? | 14/14 tables, 15/15 code objects applied first pass |
| 3 | Validation | Approve the equivalence test results? | 14/14 reconcile, 53/53 tests, 4 LOW_COVERAGE objects |
| 4 | Operations | Approve the cutover & rollback plan? | runbook/rollback/monitoring generated (AI-generated, review required) |
| App | Modernization | Approve the change plan / converted app / cutover? | 17 files; builds; boots with `ddl-auto=validate`; search verified |

Open follow-up items: **0**. Identity: 12/12 safe.
