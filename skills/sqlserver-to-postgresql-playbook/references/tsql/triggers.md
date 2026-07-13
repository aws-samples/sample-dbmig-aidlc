# Triggers

> Source: AWS SQL Server→Aurora PostgreSQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/sql-server-to-aurora-postgresql-migration-playbook/chap-sql-server-aurora-pg.tsql.triggers.html

**Conversion category:** Assisted (three-star feature compatibility, three-star automation)
**SCT automation:** Three-star automation level; SCT action code index: Triggers

## SQL Server

Triggers are special stored procedures that run automatically on events, most commonly DML. SQL Server supports `AFTER`/`FOR` (synonymous) and `INSTEAD OF` triggers on tables and views, plus DDL/DCL/system event triggers at server and database levels. SQL Server does **not** support `FOR EACH ROW` triggers — only statement-level.

- `AFTER` triggers run after the DML completes (tables only).
- `INSTEAD OF` triggers run in place of the DML (tables and views); only one per object/event.
- Multiple AFTER triggers: order partially set with `sp_settriggerorder` (first/last only).
- Change data is exposed in virtual tables `INSERTED` and `DELETED` (whole change set).
- Triggers run in the statement's transaction; a `ROLLBACK` or exception rolls back the DML.

DML audit trigger example:

```sql
CREATE TRIGGER LogInvoiceDeletes
ON Invoices
AFTER DELETE
AS
BEGIN
INSERT INTO InvoiceAuditLog (InvoiceID, Customer, TotalAmount)
SELECT InvoiceID, Customer, TotalAmount
FROM Deleted
END;
```

DDL trigger example (prevent table drop):

```sql
CREATE TRIGGER PreventTableDrop
ON DATABASE FOR DROP_TABLE
AS
BEGIN
  RAISERROR ('Tables can''t be dropped in this database', 16, 1)
  ROLLBACK TRANSACTION
END;
```

## PostgreSQL

PostgreSQL provides DML triggers (table events) and event triggers (database events like DDL). Unlike SQL Server, **PostgreSQL triggers must call a function** — no anonymous block in the trigger body. The function takes no arguments and returns type `trigger` (or `event_trigger`).

DML triggers fire `BEFORE`, `AFTER`, or `INSTEAD OF` (views), and `FOR EACH ROW` or `FOR EACH STATEMENT`:

| When fired | Event | Row-Level (FOR EACH ROW) | Statement-level (FOR EACH STATEMENT) |
|---|---|---|---|
| BEFORE | INSERT, UPDATE, DELETE | Tables and foreign tables | Tables, views, foreign tables |
| BEFORE | TRUNCATE | — | Tables |
| AFTER | INSERT, UPDATE, DELETE | Tables and foreign tables | Tables, views, foreign tables |
| AFTER | TRUNCATE | — | Tables |
| INSTEAD OF | INSERT, UPDATE, DELETE | Views | — |
| INSTEAD OF | TRUNCATE | — | — |

**Event triggers** fire on `ddl_command_start`, `ddl_command_end`, `table_rewrite`, `sql_drop`.

`CREATE TRIGGER` synopsis:

```sql
CREATE [ CONSTRAINT ] TRIGGER name { BEFORE | AFTER | INSTEAD OF } { event [ OR ... ]}
  ON table_name
  [ FROM referenced_table_name ]
  [ NOT DEFERRABLE | [ DEFERRABLE ] [ INITIALLY IMMEDIATE | INITIALLY DEFERRED ] ]
  [ REFERENCING { { OLD | NEW } TABLE [ AS ] transition_relation_name } [ ... ] ]
  [ FOR [ EACH ] { ROW | STATEMENT } ]
  [ WHEN ( condition ) ]
  EXECUTE PROCEDURE function_name ( arguments )
-- event: INSERT | UPDATE [ OF column_name [, ...] ] | DELETE | TRUNCATE
```
(`REFERENCING` is available since PostgreSQL 10 for AFTER triggers to access OLD/NEW transition tables.)

DML trigger function + trigger:

```sql
CREATE OR REPLACE FUNCTION PROJECTS_SET_NULL()
  RETURNS TRIGGER
  AS $$
  BEGIN
IF TG_OP = 'UPDATE' AND OLD.PROJECTNO != NEW.PROJECTNO OR TG_OP = 'DELETE' THEN
UPDATE EMP SET PROJECTNO = NULL WHERE EMP.PROJECTNO = OLD.PROJECTNO;
  END IF;
  IF TG_OP = 'UPDATE' THEN RETURN NULL;
    ELSIF TG_OP = 'DELETE' THEN RETURN NULL;
  END IF;
END; $$
LANGUAGE PLPGSQL;

CREATE TRIGGER TRG_PROJECTS_SET_NULL
AFTER UPDATE OF PROJECTNO OR DELETE
ON PROJECTS
FOR EACH ROW
EXECUTE PROCEDURE PROJECTS_SET_NULL();
```

Event trigger (prevent DROP):

```sql
CREATE OR REPLACE FUNCTION ABORT_DROP_COMMAND()
  RETURNS EVENT_TRIGGER
  AS $$
BEGIN
  RAISE EXCEPTION 'The % Command is Disabled', tg_tag;
END; $$
LANGUAGE PLPGSQL;

CREATE EVENT TRIGGER trg_abort_drop_command
  ON DDL_COMMAND_START
  WHEN TAG IN ('DROP TABLE', 'DROP VIEW', 'DROP FUNCTION', 'DROP SEQUENCE', 'DROP MATERIALIZED VIEW', 'DROP TYPE')
  EXECUTE PROCEDURE abort_drop_command();
```

## Summary

| Feature | SQL Server | Aurora PostgreSQL |
|---|---|---|
| DML trigger scope | Statement level only | `FOR EACH ROW` and `FOR EACH STATEMENT` |
| Access to change set | `INSERTED`/`DELETED` (multi-row virtual tables) | `OLD`/`NEW` (one-row) or transition tables |
| System event triggers | DDL, DCL, other events | Event triggers |
| Trigger run phase | `AFTER`, `INSTEAD OF` | `AFTER`, `BEFORE`, `INSTEAD OF` |
| Multi-trigger order | first/last via `sp_settriggerorder` | call function within a function |
| Drop trigger | `DROP TRIGGER <name>;` | `DROP TRIGGER <name>;` |
| Modify trigger code | `ALTER TRIGGER` | modify the function code |
| Enable/disable trigger | `ALTER TRIGGER ... ENABLE/DISABLE` | `ALTER TABLE` |
| Triggers on views | `INSTEAD OF` only | `INSTEAD OF` only |

## Conversion notes
- Split each trigger into a **trigger function** (`RETURNS TRIGGER`) plus a `CREATE TRIGGER` that calls it.
- Replace `INSERTED`/`DELETED` with `NEW`/`OLD` (row-level) or `REFERENCING ... TABLE` transition tables (statement-level, PG10+).
- Use `TG_OP` to branch by operation (INSERT/UPDATE/DELETE).
- PostgreSQL adds `BEFORE` and row-level triggers — you can simplify some statement-level SQL Server logic.
- DDL triggers → event triggers using `tg_tag`/`TAG IN (...)`.
- `ALTER TRIGGER` for code changes → edit the function; enable/disable via `ALTER TABLE ... ENABLE/DISABLE TRIGGER`.
