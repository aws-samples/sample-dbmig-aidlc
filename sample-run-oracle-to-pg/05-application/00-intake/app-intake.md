# App Intake — JavaBobsUsedBooks → migrations/demo (oracle-to-postgresql)

- **Application directory:** `/tmp/JavaBobsUsedBooks` (not a git repository — mirrored backups are
  the only restore path; noted).
- **DB migration workspace:** `migrations/demo/` — Oracle 19c `DEMO` → Aurora PostgreSQL 17.7
  `demodb.demo` (completed and signed off; see `SIGN-OFF.md`).
- **Engine pair:** `oracle-to-postgresql` → rules from `engines/oracle-to-postgresql/app/`.
- **Stack:** Java 21, Spring Boot 3.x (Maven), Spring Data JPA/Hibernate, Thymeleaf. Both
  `ojdbc17` and `postgresql` drivers already in `pom.xml` (PG driver pre-staged, unused).
- **Build command:** `mvn -q -B clean compile` (baseline: **passes**, exit 0).
  **Test command:** `mvn -q -B test` (suite exists under `src/test` — to confirm at Validation).
- **Scope:** `src/main/**` + `pom.xml`. **Excluded:** `target/` (build output — contains a stale
  `.bak`), `src/main/resources/static/` (JS/CSS assets), `src/main/resources/db/oracle/*.sql`
  (Oracle DBA/seed scripts — flag only, per module policy).
- **Pre-existing mess noted (not ours to fix silently):** 5 stray `.bak` files from a previous
  ad-hoc conversion (incl. one inside `target/`); demo classes query a `sales` table that does not
  exist in the migrated schema.
