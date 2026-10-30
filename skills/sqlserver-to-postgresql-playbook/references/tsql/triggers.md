# Triggers

> Source: AWS SQL Server→Aurora PostgreSQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/sql-server-to-aurora-postgresql-migration-playbook/chap-sql-server-aurora-pg.tsql.triggers.html

**Conversion category:** Assisted (three-star feature compatibility, three-star automation)
**SCT automation:** Three-star automation level; SCT action code index: Triggers

> **Reviewed for Aurora PostgreSQL 18** (validated on 18.6, 2026-10-29): EXECUTE PROCEDURE→EXECUTE FUNCTION, CREATE OR REPLACE TRIGGER; verified statement-level transition-table pattern named inserted/deleted (one event per trigger), INSTEAD OF on tables→BEFORE row trigger returning NULL, event triggers incl. PG 17 login allowed for rds_superuser, session_replication_role, alphabetical trigger order.

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

**Event triggers** fire on `ddl_command_start`, `ddl_command_end`, `table_rewrite`, `sql_drop`, and (PG 17) `login`. On Aurora the master user (`rds_superuser`) can create them (verified on 18.6, including `ON login`).

`CREATE TRIGGER` synopsis:

```sql
CREATE [ OR REPLACE ] [ CONSTRAINT ] TRIGGER name { BEFORE | AFTER | INSTEAD OF } { event [ OR ... ]}
  ON table_name
  [ FROM referenced_table_name ]
  [ NOT DEFERRABLE | [ DEFERRABLE ] [ INITIALLY IMMEDIATE | INITIALLY DEFERRED ] ]
  [ REFERENCING { { OLD | NEW } TABLE [ AS ] transition_relation_name } [ ... ] ]
  [ FOR [ EACH ] { ROW | STATEMENT } ]
  [ WHEN ( condition ) ]
  EXECUTE FUNCTION function_name ( arguments )   -- EXECUTE PROCEDURE is the deprecated PG 10 spelling
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
EXECUTE FUNCTION PROJECTS_SET_NULL();
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
  EXECUTE FUNCTION abort_drop_command();
```

## Converting `INSERTED`/`DELETED` (verified on Aurora PostgreSQL 18.6)

The closest match to SQL Server's set-based triggers is a **statement-level trigger with transition tables** named after the SQL Server pseudo-tables, so the body converts almost unchanged:

```sql
CREATE OR REPLACE FUNCTION log_invoice_deletes() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  INSERT INTO invoice_audit_log (invoiceid, customer, totalamount)
  SELECT invoiceid, customer, totalamount FROM deleted;
  RETURN NULL;
END $$;

CREATE OR REPLACE TRIGGER log_invoice_deletes
AFTER DELETE ON invoices
REFERENCING OLD TABLE AS deleted
FOR EACH STATEMENT EXECUTE FUNCTION log_invoice_deletes();

-- AFTER UPDATE: both sets
CREATE TRIGGER t_upd AFTER UPDATE ON invoices
REFERENCING OLD TABLE AS deleted NEW TABLE AS inserted
FOR EACH STATEMENT EXECUTE FUNCTION trg_invoices_upd();
```

- A trigger with transition tables can cover **only one event** (verified: `AFTER INSERT OR UPDATE … REFERENCING` fails with 0A000). Split a SQL Server `AFTER INSERT, UPDATE` trigger into one trigger per event; they can share a function that branches on `TG_OP`.
- Transition tables are available on `AFTER` triggers only, not `BEFORE` or `INSTEAD OF`.
- `IF UPDATE(col)` / `COLUMNS_UPDATED()` → `AFTER UPDATE OF col` in the trigger definition, or compare `n.col IS DISTINCT FROM o.col` joining `inserted` to `deleted` on the key. `UPDATE OF col` fires when the column is in the `SET` list even if the value is unchanged, matching `UPDATE()`.
- Row-level `FOR EACH ROW` triggers with `OLD`/`NEW` are fine when the body handles one row; SQL Server code written as `SELECT @x = col FROM inserted` (single-row assumption) is often safer as a row trigger.
- `INSTEAD OF` triggers on **tables** are rejected (verified: `"inv" is a table`). Convert to a `BEFORE … FOR EACH ROW` trigger that does the replacement work and `RETURN NULL` (skips the original row, verified). `INSTEAD OF` on views converts directly.
- `ROLLBACK TRANSACTION` in a trigger → `RAISE EXCEPTION` (aborts the statement and the transaction).
- `@@ROWCOUNT` at the top of the trigger (`IF @@ROWCOUNT = 0 RETURN`) → `IF NOT EXISTS (SELECT 1 FROM inserted) THEN RETURN NULL; END IF;`.
- `TRIGGER_NESTLEVEL()` → `pg_trigger_depth()`. `sp_settriggerorder` → PostgreSQL fires triggers of the same timing **in alphabetical order by name**; rename triggers (`t01_…`, `t02_…`) to fix the order.
- `DISABLE TRIGGER ALL ON t` → `ALTER TABLE t DISABLE TRIGGER ALL` (needs table owner; FK triggers need superuser) or, for a bulk load, `SET session_replication_role = replica` (allowed for the Aurora master user, verified) which also skips FK checks. The toolkit defers triggers until after the data load instead (`apply-schema --post-data`).
- Server-level `LOGON` triggers → `CREATE EVENT TRIGGER … ON login` (PG 17). A failing login trigger blocks all logins; test it and keep a session open while deploying.
- DDL triggers `ON DATABASE FOR CREATE_TABLE, ALTER_TABLE …` → `ddl_command_end` event trigger using `pg_event_trigger_ddl_commands()`; `DROP_*` → `sql_drop` with `pg_event_trigger_dropped_objects()`. `EVENTDATA()` XML → those functions' columns.

## Summary

| Feature | SQL Server | Aurora PostgreSQL |
|---|---|---|
| DML trigger scope | Statement level only | `FOR EACH ROW` and `FOR EACH STATEMENT` |
| Access to change set | `INSERTED`/`DELETED` (multi-row virtual tables) | `OLD`/`NEW` (one-row) or transition tables |
| System event triggers | DDL, DCL, other events | Event triggers |
| Trigger run phase | `AFTER`, `INSTEAD OF` | `AFTER`, `BEFORE`, `INSTEAD OF` |
| Multi-trigger order | first/last via `sp_settriggerorder` | alphabetical by trigger name |
| Drop trigger | `DROP TRIGGER <name>;` | `DROP TRIGGER <name>;` |
| Modify trigger code | `ALTER TRIGGER` / `CREATE OR ALTER TRIGGER` | `CREATE OR REPLACE FUNCTION` (body) / `CREATE OR REPLACE TRIGGER` (PG 14, definition) |
| Enable/disable trigger | `ENABLE/DISABLE TRIGGER … ON t` | `ALTER TABLE t ENABLE/DISABLE TRIGGER …` |
| Triggers on views | `INSTEAD OF` only | `INSTEAD OF` (row-level only) |
| `INSTEAD OF` on tables | supported | not supported → `BEFORE … FOR EACH ROW` returning `NULL` |
| Logon triggers | server-level `FOR LOGON` | `CREATE EVENT TRIGGER … ON login` (PG 17) |

## Conversion notes
- Split each trigger into a **trigger function** (`RETURNS TRIGGER`) plus a `CREATE TRIGGER` that calls it.
- Replace `INSERTED`/`DELETED` with `REFERENCING OLD TABLE AS deleted NEW TABLE AS inserted` on an `AFTER … FOR EACH STATEMENT` trigger (one event per trigger), or with `NEW`/`OLD` in a row-level trigger.
- Use `EXECUTE FUNCTION`, not the deprecated `EXECUTE PROCEDURE`.
- Use `TG_OP` to branch by operation (INSERT/UPDATE/DELETE).
- PostgreSQL adds `BEFORE` and row-level triggers — you can simplify some statement-level SQL Server logic.
- DDL triggers → event triggers using `tg_tag`/`TAG IN (...)`.
- `ALTER TRIGGER` for code changes → edit the function; enable/disable via `ALTER TABLE ... ENABLE/DISABLE TRIGGER`.
