# EXAMPLE — Application override rules (Oracle → MySQL) (template)

> This is an EXAMPLE/template, not active rules. Copy it to a real file (e.g.
> `datasource-config.md`) and edit, or delete it. Files in this folder take precedence
> over `../app-sql-rules.md` when they conflict. Mark each overriding rule with "Override:".

## Frameworks / driver
- The application is Java 17 + Spring Boot + Hibernate. Target MySQL driver and Hibernate
  dialect must be used; do not change the ORM or upgrade framework versions (like-for-like).

## Datasource configuration
- Override: connection URL, pool sizing and SSL mode are managed centrally — change only the
  driver/dialect and dialect-specific properties, leave pool/timeout values untouched.

## Embedded SQL conventions
- Override: keep existing named parameters (`:name`); do not rewrite to positional.
- Prefer ANSI-standard functions; replace Oracle-specific functions with the customer-approved
  MySQL equivalent listed in `embedded-sql-conventions.md`.

## Error handling
- Override: the app branches on specific Oracle error codes; map each to the MySQL
  code/SQLSTATE per `error-handling.md` and preserve the surrounding retry logic verbatim.

## Forbidden
- Do not introduce new ORM features, second-level caches, or native queries where the
  original used portable HQL/JPQL.
