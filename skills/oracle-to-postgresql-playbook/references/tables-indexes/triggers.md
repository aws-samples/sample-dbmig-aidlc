# Triggers

> Source: AWS Oracle→Aurora PostgreSQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/oracle-to-aurora-postgresql-migration-playbook/chap-oracle-aurora-pg.tables.triggers.html

**Conversion category:** Assisted (four-star feature compatibility, three-star automation)
**SCT automation:** Triggers action code index. Different paradigm/syntax; system triggers not supported by PostgreSQL.

> **Reviewed for Aurora PostgreSQL 18** (validated on 18.6, 2026-10-29): PG 17 `login` event trigger (verified), PG 14 `CREATE OR REPLACE TRIGGER` (verified), `EXECUTE FUNCTION`, alphabetical firing order, compound-trigger mapping, `IS DISTINCT FROM` fix in the example.

## Oracle
A trigger runs when a specified event occurs, tied to a table, view, schema, or the database. Can fire after DML (`INSERT`/`UPDATE`/`DELETE`), DDL (`CREATE`/`ALTER`/`DROP`), or DB events (`SERVERERROR`, `LOGON`, `LOGOFF`, `STARTUP`, `SHUTDOWN`).

Trigger types:
- **DML** — on tables/views, fire BEFORE or AFTER insert/update/delete.
- **INSTEAD OF** — on non-editable views.
- **SYSTEM/event** — database or schema level (logon/logoff, startup/shutdown, server errors, etc.).

Triggers can contain anonymous PL/SQL blocks directly in the trigger body. Use `:OLD` and `:NEW` to reference row values.

```sql
CREATE OR REPLACE TRIGGER PROJECTS_SET_NULL
  AFTER DELETE OR UPDATE OF PROJECTNO ON PROJECTS
  FOR EACH ROW
  BEGIN
    IF UPDATING AND :OLD.PROJECTNO != :NEW.PROJECTNO OR DELETING THEN
      UPDATE EMP SET EMP.PROJECTNO = NULL
      WHERE EMP.PROJECTNO = :OLD.PROJECTNO;
    END IF;
END;
/
```

Schema/DDL trigger preventing drops:
```sql
CREATE OR REPLACE TRIGGER PREVENT_DROP_TRIGGER
  BEFORE DROP ON HR.SCHEMA
  BEGIN
    RAISE_APPLICATION_ERROR (num => -20000, msg => 'Cannot drop object');
END;
/
```

## PostgreSQL
PostgreSQL triggers must call a **function** — no anonymous PL/pgSQL blocks in the trigger body. The function takes no arguments and returns type `trigger` (or `event_trigger`). Use `NEW`/`OLD` (dot notation, not `:`).

Two kinds: **DML triggers** and **event triggers** (fire on DDL events).

```sql
CREATE [ CONSTRAINT ] TRIGGER name { BEFORE | AFTER | INSTEAD OF } { event [ OR ... ]}
  ON table_name
  [ FROM referenced_table_name ]
  [ NOT DEFERRABLE | [ DEFERRABLE ] [ INITIALLY IMMEDIATE | INITIALLY DEFERRED ] ]
  [ REFERENCING { { OLD | NEW } TABLE [ AS ] transition_relation_name } [ ... ] ]
  [ FOR [ EACH ] { ROW | STATEMENT } ]
  [ WHEN ( condition ) ]
  EXECUTE FUNCTION function_name ( arguments )   -- PG 11+; EXECUTE PROCEDURE is the legacy spelling
-- event: INSERT | UPDATE [ OF column ] | DELETE | TRUNCATE
-- PG 14+: CREATE OR REPLACE TRIGGER (verified on 18.6)
```
`REFERENCING` (PostgreSQL 10+) works with `AFTER` triggers to access `OLD`/`NEW TABLE` transition rows.

DML triggers fire BEFORE (before constraints checked; can skip/modify the row for INSERT/UPDATE), AFTER (all changes visible), or INSTEAD OF (on views). `FOR EACH ROW` or `FOR EACH STATEMENT`.

| When | Event | Row-level | Statement-level |
|---|---|---|---|
| BEFORE | INSERT/UPDATE/DELETE | Tables, foreign tables | Tables, views, foreign tables |
| BEFORE | TRUNCATE | N/A | Tables |
| AFTER | INSERT/UPDATE/DELETE | Tables, foreign tables | Tables, views, foreign tables |
| AFTER | TRUNCATE | N/A | Tables |
| INSTEAD OF | INSERT/UPDATE/DELETE | Views | N/A |

**Event triggers**: `ddl_command_start`, `ddl_command_end`, `table_rewrite`, `sql_drop`, and **`login`** (PG 17+, verified on Aurora 18.6 as the master user). `login` is the equivalent of Oracle `AFTER LOGON ON DATABASE`.

Equivalent of the Oracle DML trigger — first the function, then the trigger:

```sql
CREATE OR REPLACE FUNCTION PROJECTS_SET_NULL()
  RETURNS TRIGGER AS $$
  BEGIN
  IF TG_OP = 'UPDATE' AND OLD.PROJECTNO IS DISTINCT FROM NEW.PROJECTNO OR TG_OP = 'DELETE' THEN
    UPDATE EMP SET PROJECTNO = NULL WHERE EMP.PROJECTNO = OLD.PROJECTNO;
  END IF;
  IF TG_OP = 'UPDATE' THEN RETURN NULL;
    ELSIF TG_OP = 'DELETE' THEN RETURN NULL;
  END IF;
  END; $$ LANGUAGE PLPGSQL;

CREATE TRIGGER TRG_PROJECTS_SET_NULL
  AFTER UPDATE OF PROJECTNO OR DELETE ON PROJECTS
  FOR EACH ROW EXECUTE FUNCTION PROJECTS_SET_NULL();
```

Equivalent of an Oracle DDL/schema trigger via an event trigger:
```sql
CREATE OR REPLACE FUNCTION ABORT_DROP_COMMAND()
    RETURNS EVENT_TRIGGER AS $$
  BEGIN
    RAISE EXCEPTION 'The % Command is Disabled', tg_tag;
  END; $$ LANGUAGE PLPGSQL;

CREATE EVENT TRIGGER trg_abort_drop_command
  ON DDL_COMMAND_START
  WHEN TAG IN ('DROP TABLE', 'DROP VIEW', 'DROP FUNCTION',
    'DROP SEQUENCE', 'DROP MATERIALIZED VIEW', 'DROP TYPE')
  EXECUTE FUNCTION abort_drop_command();
```

### Mapping summary
| Feature | Oracle | PostgreSQL |
|---|---|---|
| Row-level DML trigger | `BEFORE UPDATE ... FOR EACH ROW BEGIN ... END;` | `... FOR EACH ROW EXECUTE FUNCTION myfn();` |
| Statement-level | `BEFORE UPDATE ... BEGIN ... END;` | `... FOR EACH STATEMENT EXECUTE FUNCTION myfn();` |
| System/event trigger | `BEFORE DROP ON hr.SCHEMA` | `CREATE EVENT TRIGGER ... ON ddl_command_start` |
| Row references | `:NEW` / `:OLD` | `NEW` / `OLD` |
| LOGON trigger | `AFTER LOGON ON DATABASE` | `CREATE EVENT TRIGGER … ON login` (PG 17+); for plain `ALTER SESSION` settings prefer `ALTER ROLE … SET` |
| DB event trigger (startup/shutdown, LOGOFF, SERVERERROR) | Supported | N/A |
| Compound trigger | `COMPOUND TRIGGER` | Separate statement-level and row-level triggers, or one `AFTER … FOR EACH STATEMENT` trigger with `REFERENCING NEW TABLE AS …` (transition tables) |
| Firing order | `FOLLOWS` / `PRECEDES` | Triggers of the same kind fire in **alphabetical order of trigger name**. Rename (`trg_10_…`, `trg_20_…`) to reproduce `FOLLOWS` |
| Conditional | `WHEN (new.x > 0)` | `WHEN (NEW.x > 0)` (same idea, no colon) |
| Drop trigger | `DROP TRIGGER trg;` | `DROP TRIGGER trg ON employees;` |
| Modify logic | `CREATE OR REPLACE TRIGGER` | `CREATE OR REPLACE FUNCTION` (trigger unchanged), or `CREATE OR REPLACE TRIGGER` (PG 14+) to change the trigger definition |
| Enable/disable | `ALTER TRIGGER trg ENABLE/DISABLE;` | `ALTER TABLE t ENABLE/DISABLE TRIGGER trg;` |

## Conversion notes
- PostgreSQL requires a separate trigger **function**; the trigger body cannot contain inline PL/pgSQL. Refactor each Oracle trigger into function + `CREATE TRIGGER`.
- Replace `:NEW`/`:OLD` with `NEW`/`OLD`; use `TG_OP` to branch on INSERT/UPDATE/DELETE instead of `INSERTING`/`UPDATING`/`DELETING`. `UPDATING('col')` → `OLD.col IS DISTINCT FROM NEW.col` (or `UPDATE OF col` in the trigger definition, which fires when the column is listed in `SET` even if the value is unchanged).
- Use `IS DISTINCT FROM`, not `!=`/`<>`, when comparing `OLD` and `NEW`; `!=` yields NULL when either side is NULL and the branch is skipped.
- `BEFORE` row triggers must `RETURN NEW` (or `OLD` for DELETE) to let the row through; returning NULL silently skips the row.
- **System/database-event triggers**: `LOGON` → `login` event trigger (PG 17+). STARTUP, SHUTDOWN, LOGOFF and SERVERERROR have **no PostgreSQL equivalent** (use RDS event notifications / CloudWatch Logs for SERVERERROR-style alerting). DDL-level logic maps to event triggers (`ddl_command_start`/`end`, `sql_drop`). Event triggers on Aurora can be created by the master user (`rds_superuser`).
- `DROP TRIGGER` must name the table in PostgreSQL.
- To change logic, replace the function (`CREATE OR REPLACE FUNCTION`); the trigger definition stays the same.
- Beware multi-fire scenarios: `INSERT ... ON CONFLICT DO UPDATE` can fire both insert and update; FK enforcement (`ON UPDATE CASCADE`, `ON DELETE SET NULL`) can fire UPDATE/DELETE triggers.
