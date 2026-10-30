# App intake — JavaBobsUsedBooks

| Item | Value |
|---|---|
| App dir | `<app-dir>/JavaBobsUsedBooks` (a working copy taken from the workshop host; the original there is untouched) |
| Stack | Spring Boot 4.0.6, Java 21, Maven, Spring Data JPA / Hibernate 7, Thymeleaf, plus raw JDBC demo classes and a JDBC utility |
| Migration to conform to | `migrations/<project>/` (Oracle `DEMO` → Aurora PostgreSQL 18.6 `demo`) |
| Engine pair | `oracle-to-postgresql` (`engines/oracle-to-postgresql/app/`) |
| Build / run | `mvn -q -B clean compile`; boot `mvn spring-boot:run` with `DB_*` environment variables |
| Git | **not a git repo** → the mirrored backup is the only rollback → `backup_mode: full-tree` |
| Source-dialect state | still Oracle (ojdbc17, OracleDialect, `CONTAINS/SCORE`) — converted from the original |
| Scope | `src/`, `pom.xml` (build output, vendored static assets and `.bak` leftovers excluded) |
