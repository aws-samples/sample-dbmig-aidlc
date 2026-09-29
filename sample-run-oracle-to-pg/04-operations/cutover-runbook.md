> ⚠️ **AI-GENERATED — review before use.** Produced by dbmig-aidlc from this migration's context; validate in a non-production environment before relying on it.

# Cutover runbook — DEMO → demo

| # | Step | Owner | Rollback trigger |
|---|---|---|---|
| 0.1 | Converted application build ready (see `05-application/04-operations/app-cutover.md`) | App team | build not green |
| 1 | Freeze writes on the Oracle source; final snapshot of both sides | DBA | — |
| 2 | Final data sync (AWS DMS full load + CDC for production; `dbmig migrate-data` is dev/test only) | DBA | DMS task errors / lag not converging |
| 3 | `./dbmig compare --schema DEMO --project <P>` — all tables match | DBA | any mismatch |
| 4 | **Identity reset:** `./dbmig reset-identity --schema DEMO --target-schema demo --project <P> --apply` — exits non-zero unless all 12 identity columns verify (step generated from the catalog: `identity-reset-DEMO.md`) | DBA | non-zero exit |
| 5 | Deploy the converted app with the PostgreSQL datasource (credentials from Secrets Manager) | App team | boot fails / `ddl-auto=validate` error |
| 6 | Smoke: home, `/books`, `/fulltextsearch?query=gothic` (GIN index), cover image, admin login | App team | any 5xx |
| 7 | Open traffic; watch monitoring.md for 2 h | On-call | error-rate / latency thresholds |
