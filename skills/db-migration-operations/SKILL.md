---
name: db-migration-operations
description: Operations & Cutover phase of an AI-DLC database migration. Use after Validation is approved, or when the user asks to plan cutover, go-live, rollback, or post-migration monitoring for a database migration. Produces a cutover runbook, a rollback plan, and a monitoring checklist; for production data movement it hands off to AWS DMS (including change data capture for minimal downtime). Writes artifacts to migrations/<project>/04-operations/.
---

# Operations & Cutover

This is the **Operations** phase. Validation has proven equivalence; now plan the move to
production safely, with a way back. Mirrors AI-DLC Operations: deploy and monitor from
accumulated context, human signs off.

## Inputs
- Approved validation results (`03-validation/equivalence-report.md` +
  `03-validation/reconcile_report.yaml`)
- Conversion log and migration plan (for scope and known caveats)
- `connections.yaml`, `migration-config.yaml`

## Step 1 — Cutover strategy
Pick and document the approach with the user:
- **Big-bang (downtime)**: quiesce source, final data sync, switch app, validate, open.
  Simplest; needs a maintenance window.
- **Minimal-downtime (CDC)**: bulk load + AWS DMS change data capture to keep the target in
  sync, then a short switchover. For large/24x7 systems. See the playbook
  `<pair>-playbook/references/tools/aws-dms.md` for CDC setup (substitute the active engine
  pair).

Framework one-time loads (`dbmig migrate-data`) are for dev/test only — production data movement
should use AWS DMS.

## Step 2 — Cutover runbook
Write `04-operations/cutover-runbook.md` as an ordered, time-estimated checklist:
1. Pre-cutover: final schema diff, target capacity check, backups/snapshots, freeze changes.
2. Data: final sync / DMS cutover, sequence/identity reset to current source max values.
3. Application: connection-string / driver switch (note JDBC/ODBC differences), feature flags.
4. Smoke tests: run the validation suite's critical queries against production target.
5. Open to traffic; monitor.
Include owner and rollback trigger for each step.

## Step 3 — Rollback plan
Write `04-operations/rollback-plan.md` (required if `migration-config.yaml
cutover.require_rollback_plan` is true):
- Point of no return and the decision criteria to roll back.
- How to revert app connections to the source.
- Data divergence handling (writes that landed on the target after cutover).
- Keep the source intact and reachable until a defined soak period passes.

## Step 4 — Monitoring
Write `04-operations/monitoring.md`: post-cutover checks for the first hours/days —
error rates, slow queries (PG `pg_stat_statements`), connection counts, replication/CDC lag,
autovacuum/bloat, and the app-level KPIs that prove correctness. Reference the playbook
monitoring and performance-tuning chapters.

## Gate
Present the runbook, rollback plan, and monitoring checklist. **Stop at the gate: "Approve
the cutover & rollback plan?"** Cutover execution itself is a high-risk, production action —
only proceed under explicit user direction, step by step, never unattended.

## Safety
- Production cutover and data movement are high-risk. Confirm each destructive/irreversible
  step. Never drop or truncate source data. Verify backups exist before the point of no
  return.
