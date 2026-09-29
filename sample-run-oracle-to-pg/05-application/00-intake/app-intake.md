# App intake — JavaBobsUsedBooks

| Item | Value |
|---|---|
| App dir | `<app-dir>/JavaBobsUsedBooks` (a working copy — the original on the workshop host is untouched) |
| Stack | Spring Boot 4.0.6, Java 21, Maven, Spring Data JPA / Hibernate 7, Thymeleaf, plus raw JDBC demo classes |
| Migration to conform to | `migrations/<project>/` (DEMO → demo) |
| Build / run | `mvn -q -B clean compile`; boot `mvn spring-boot:run` with `DB_*` env vars |
| Git | **not a git repo** → the mirrored backup is the only rollback → `backup_mode: full-tree` (whole in-scope tree copied before the first edit) |
| Scope | `src/`, `pom.xml` (build output, vendored static assets excluded) |
