# App contract — what the DB migration changed → what the app must change

| DB change (source) | Required app change |
|---|---|
| Oracle → Aurora PostgreSQL 18.6, schema `demo` (`00-intake/intake.md`) | PostgreSQL JDBC URL with `currentSchema=demo&sslmode=require`; `org.postgresql.Driver`; drop `OracleDialect`; drop `ojdbc17` (`engines/oracle-to-postgresql/app/app-config.yaml`) |
| `NUMBER(1)` flags → `smallint` 0/1 (`02-construction/conversion-log.md`; validation carry-forward 1) | `Boolean` fields: `@JdbcTypeCode(SqlTypes.SMALLINT)`, remove `columnDefinition="NUMBER(1)"` |
| `DATE` → `timestamp(0)` (carry-forward 2) | `LocalDate` fields: `@JdbcTypeCode(SqlTypes.TIMESTAMP)` |
| `BLOB` → `bytea` (carry-forward 3) | drop `@Lob`, add `@JdbcTypeCode(SqlTypes.VARBINARY)` |
| `fulltext_redesign` → GIN on `to_tsvector('english', coalesce(search_text,''))` (carry-forward 4) | rewrite `CONTAINS/SCORE` to that exact expression + `ts_rank`; the query builder must stop emitting Oracle Text syntax |
| Packages flattened `<package>_<subprogram>`; errors SQLSTATE `U0001`/`U0002` (carry-forward 5) | no app call sites to package routines (scan D: 1 call, to a routine absent in the source) |
| `COMMIT` removed from 4 procedures | no app call sites |
| Identifiers folded to lower case | native SQL must not rely on quoted upper-case names |
