> ⚠️ **AI-GENERATED — review before use.** Produced by dbmig-aidlc from this migration's context; validate in a non-production environment before relying on it.

# Cutover runbook — BobsUsedBookStore → Aurora PostgreSQL

| # | Step | Rollback trigger |
|---|---|---|
| 0.1 | Converted .NET build ready (`05-application`) | build red |
| 1 | Freeze writes on SQL Server; snapshots | — |
| 2 | Final sync (AWS DMS full load + CDC) | task errors |
| 3 | `./dbmig compare --schema dbo --project <P>` | mismatch |
| 4 | `./dbmig reset-identity --schema dbo --project <P> --apply` (14 identity columns) | non-zero exit |
| 5 | Deploy app with Npgsql connection (secret → host/port/user/password; `SearchPath=dbo`) | startup error |
| 6 | Smoke: home, search **lower-case** term (case-insensitive), book details, admin inventory | any 5xx / empty search |
