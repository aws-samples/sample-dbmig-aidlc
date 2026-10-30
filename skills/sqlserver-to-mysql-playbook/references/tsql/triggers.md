# Triggers for T-SQL

> Source: AWS SQL Server→Aurora MySQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/sql-server-to-aurora-mysql-migration-playbook/chap-sql-server-aurora-mysql.tsql.triggers.html

**Conversion category:** Manual (Two star feature compatibility)
**SCT automation:** Four star automation level

> **Reviewed for Aurora MySQL 8.4 and 3** (validated on 8.4.8 and 3.13.0, 2026-10-29): Fixed the example (CREATE OR REPLACE, AS, FROM OLD are invalid — verified working form); INSTEAD OF limits; verified trigger rules (one event per trigger, no self-table DML 1442, no COMMIT/dynamic SQL, AFTER can't set NEW); session-variable disable pattern; UPDATE() → NULL-safe comparison.

## SQL Server

Triggers are special stored procedures that run automatically in response to events, mostly DML. SQL Server supports `AFTER`/`FOR` (synonymous) and `INSTEAD OF` triggers on tables and views, plus DDL/DCL/system event triggers at server and database levels. **No `FOR EACH ROW`** — SQL Server triggers are **statement-level**.

- `AFTER` triggers: after the DML completes; tables only.
- `INSTEAD OF` triggers: run in place of the DML; tables and views; only one per object/event.
- Multiple `AFTER` triggers: partial ordering via `sp_settriggerorder` (first/last only).

Changed data is exposed in two virtual multi-row tables: `INSERTED` and `DELETED`. Triggers run inside the triggering statement's transaction; an explicit `ROLLBACK` or exception rolls back the DML too.

### Examples

```sql
-- AFTER DELETE audit trigger
CREATE TRIGGER LogInvoiceDeletes
ON Invoices
AFTER DELETE
AS
BEGIN
INSERT INTO InvoiceAuditLog (InvoiceID, Customer, TotalAmount)
SELECT InvoiceID, Customer, TotalAmount
FROM Deleted
END;

-- DDL trigger preventing table drops
CREATE TRIGGER PreventTableDrop
ON DATABASE FOR DROP_TABLE
AS
BEGIN
    RAISERROR ('Tables can''t be dropped in this database', 16, 1)
    ROLLBACK TRANSACTION
END;
```

## MySQL

Aurora MySQL provides **DML triggers only**: `BEFORE`/`AFTER` for `INSERT`/`UPDATE`/`DELETE`, with full run-order control. Triggers run **once per row** (`FOR EACH ROW`). No DDL/system event triggers. Supports `BEFORE` triggers (SQL Server doesn't). Change set exposed in one-row virtual tables `OLD` and `NEW` (which are updatable in `BEFORE` triggers).

### Syntax

```sql
CREATE [DEFINER = { user | CURRENT_USER }] TRIGGER <Trigger Name>
{ BEFORE | AFTER } { INSERT | UPDATE | DELETE }
ON <Table Name>
FOR EACH ROW
[{ FOLLOWS | PRECEDES } <Other Trigger Name>]
<Trigger Code Body>
```

### Example

```sql
-- (the original used CREATE OR REPLACE, AS and SELECT … FROM OLD, which are all invalid in MySQL — verified)
CREATE TRIGGER LogInvoiceDeletes
AFTER DELETE ON Invoices
FOR EACH ROW
INSERT INTO InvoiceAuditLog (InvoiceID, Customer, TotalAmount, DeleteDate, DeletedBy)
VALUES (OLD.InvoiceID, OLD.Customer, OLD.TotalAmount, NOW(), CURRENT_USER());
-- a 2-row DELETE logged 2 audit rows (verified on 3.13 and 8.4.8)
```
(Note: `GETDATE()` is not supported in MySQL — use `NOW()`.)

## Conversion notes

- Statement-level → `FOR EACH ROW`. A one-row set is still valid, so most code works unchanged. But you can't access other rows modified in the same statement (NEW/OLD reference only the current row) — aggregate-over-statement logic needs rework. If the SQL Server trigger loops/cursors over rows, remove the loop/cursor.
- Change set: `INSERTED` → `NEW`, `DELETED` → `OLD`.
- `INSTEAD OF` → `BEFORE` trigger only when the SQL Server trigger re-runs the same DML with adjusted values: modify `NEW` instead (applied when the row is written). A `BEFORE` trigger **cannot skip** the base DML except by raising an error (`SIGNAL`), so `INSTEAD OF` triggers that redirect writes elsewhere (or on views) must become stored procedures that the application calls.
- Multi-trigger order: `sp_settriggerorder` → `PRECEDES`/`FOLLOWS`.
- Not supported in Aurora MySQL: DDL/system event triggers, triggers on views, `ALTER TRIGGER` (modify), enable/disable triggers.
  - Modify: drop and recreate.
  - Enable/disable workaround: a flags table, or a session user variable checked at the top of the body (`IF @disable_triggers = 1 THEN … ELSE … END IF`, verified) — the variable only affects the setting session, like `DISABLE TRIGGER` for a load.

Verified on Aurora MySQL 3.13 and 8.4.8:
- `CREATE OR REPLACE TRIGGER` is a syntax error; use `DROP TRIGGER IF EXISTS` + `CREATE TRIGGER`, or `CREATE TRIGGER IF NOT EXISTS` (accepted).
- One event per trigger: `AFTER INSERT OR UPDATE` is a syntax error; split SQL Server `FOR INSERT, UPDATE` triggers into one trigger per event (they can call a shared procedure).
- Triggers cannot modify the table that fired them (error 1442), cannot `COMMIT`, and cannot use dynamic SQL (errors 1422/1336); an `AFTER` trigger cannot assign `NEW` (error 1362).
- Statement-level logic over `INSERTED`/`DELETED` (for example `IF (SELECT COUNT(*) FROM inserted) > 1`, set-based audit `INSERT … SELECT FROM inserted`) must be rewritten per row; `UPDATE(col)` / `COLUMNS_UPDATED()` → compare `NEW.col <=> OLD.col` (NULL-safe).
- `ROLLBACK` in a trigger → `SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = …` (the statement fails and is rolled back).
- Logon triggers / DDL triggers (`ON DATABASE FOR CREATE_TABLE`) → no equivalent; use CloudWatch audit logs (Advanced Auditing) or IAM policies.
- The toolkit applies triggers after the data load (`apply-schema --post-data`), so loads are not slowed or double-processed.

| Feature | SQL Server | Aurora MySQL | Workaround |
|---|---|---|---|
| DML trigger scope | Statement-level | `FOR EACH ROW` only | Usually no change; remove loops/cursors |
| Access to change set | `INSERTED`, `DELETED` (multi-row) | `NEW`, `OLD` (one-row) | Use `NEW`/`OLD` |
| System event triggers | DDL, DCL, etc. | Not supported | — |
| Trigger phase | `AFTER`, `INSTEAD OF` | `AFTER`, `BEFORE` | `INSTEAD OF`→`BEFORE`; OLD/NEW updatable |
| Multi-trigger order | `sp_settriggerorder` (first/last) | `PRECEDES`/`FOLLOWS` (any order) | |
| Drop trigger | `DROP TRIGGER <name>;` | `DROP TRIGGER <name>;` | Compatible |
| Modify trigger | `ALTER TRIGGER` / `CREATE OR ALTER` | Not supported (`CREATE OR REPLACE` is a syntax error, verified) | Drop and recreate |
| Multiple events | `FOR INSERT, UPDATE` | One event per trigger | one trigger per event |
| Enable/disable | `ALTER TRIGGER … ENABLE/DISABLE` | Not supported | Flags table + `IF` |
| Triggers on views | `INSTEAD OF` only | Not supported | — |
