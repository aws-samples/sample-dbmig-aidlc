# Triggers for T-SQL

> Source: AWS SQL Server→Aurora MySQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/sql-server-to-aurora-mysql-migration-playbook/chap-sql-server-aurora-mysql.tsql.triggers.html

**Conversion category:** Manual (Two star feature compatibility)
**SCT automation:** Four star automation level

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
CREATE OR REPLACE TRIGGER LogInvoiceDeletes
ON Invoices
FOR EACH ROW
AFTER DELETE
AS
    BEGIN
    INSERT INTO InvoiceAuditLog (InvoiceID, Customer, TotalAmount, DeleteDate, DeletedBy)
    SELECT InvoiceID, Customer, TotalAmount, NOW(), CURRENT_USER()
    FROM OLD
END;
```
(Note: `GETDATE()` is not supported in MySQL — use `NOW()`.)

## Conversion notes

- Statement-level → `FOR EACH ROW`. A one-row set is still valid, so most code works unchanged. But you can't access other rows modified in the same statement (NEW/OLD reference only the current row) — aggregate-over-statement logic needs rework. If the SQL Server trigger loops/cursors over rows, remove the loop/cursor.
- Change set: `INSERTED` → `NEW`, `DELETED` → `OLD`.
- `INSTEAD OF` → `BEFORE` trigger; remove the explicit re-run of the DML (not needed). Modify `OLD`/`NEW` to change the change set (applied when trigger completes).
- Multi-trigger order: `sp_settriggerorder` → `PRECEDES`/`FOLLOWS`.
- Not supported in Aurora MySQL: DDL/system event triggers, triggers on views, `ALTER TRIGGER` (modify), enable/disable triggers.
  - Modify: drop and recreate.
  - Enable/disable workaround: a flags table + `IF` conditional flow control in the trigger body.

| Feature | SQL Server | Aurora MySQL | Workaround |
|---|---|---|---|
| DML trigger scope | Statement-level | `FOR EACH ROW` only | Usually no change; remove loops/cursors |
| Access to change set | `INSERTED`, `DELETED` (multi-row) | `NEW`, `OLD` (one-row) | Use `NEW`/`OLD` |
| System event triggers | DDL, DCL, etc. | Not supported | — |
| Trigger phase | `AFTER`, `INSTEAD OF` | `AFTER`, `BEFORE` | `INSTEAD OF`→`BEFORE`; OLD/NEW updatable |
| Multi-trigger order | `sp_settriggerorder` (first/last) | `PRECEDES`/`FOLLOWS` (any order) | |
| Drop trigger | `DROP TRIGGER <name>;` | `DROP TRIGGER <name>;` | Compatible |
| Modify trigger | `ALTER TRIGGER` | Not supported | Drop and recreate |
| Enable/disable | `ALTER TRIGGER … ENABLE/DISABLE` | Not supported | Flags table + `IF` |
| Triggers on views | `INSTEAD OF` only | Not supported | — |
