> ⚠️ **AI-GENERATED — review before use.** Produced by dbmig-aidlc from this migration's context; validate in a non-production environment before relying on it.

# App cutover

- Artifact: the converted build (`mvn -B package`), deployed with env `DB_HOST`, `DB_PORT`, `DB_NAME`,
  `DB_USERNAME`, `DB_PASSWORD` (from Secrets Manager — never in `application.properties`).
- Order: DB runbook steps 1–4 → deploy app (step 5) → smoke (step 6). Rollback: previous build + Oracle
  datasource (before the point of no return).
- Post-cutover checks exercise the converted paths: full-text search (hits + index scan), cover images
  (bytea), a login (smallint flags), order history dates (timestamp→LocalDate).
- Open risks with owners: fuzzy search loss (product), pre-existing broken demo classes / `get_customer_history` (app team).
