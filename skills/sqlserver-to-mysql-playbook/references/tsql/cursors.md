# Cursors for T-SQL

> Source: AWS SQL Server→Aurora MySQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/sql-server-to-aurora-mysql-migration-playbook/chap-sql-server-aurora-mysql.tsql.cursors.html

**Conversion category:** Assisted (Three star feature compatibility)
**SCT automation:** Three star automation level

> **Reviewed for Aurora MySQL 8.4 and 3** (validated on 8.4.8 and 3.13.0, 2026-10-29): Verified SELECT INTO / NOT FOUND trap, error 1325, variable-bound cursor parameters, SCROLL rejected; CURRENT OF and dynamic-cursor workarounds.

## SQL Server

Cursors provide row-by-row sequential access to a result set as an alternative to set-based operations. Capabilities: position at specific rows (absolute/relative offsets), retrieve a row or block, modify data at cursor position, isolate concurrent modifications. Usable in scripts, stored procedures, and triggers.

### Syntax

```sql
DECLARE <Cursor Name>
CURSOR [LOCAL | GLOBAL]
    [FORWARD_ONLY | SCROLL]
    [STATIC | KEYSET | DYNAMIC | FAST_FORWARD]
    [ READ_ONLY | SCROLL_LOCKS | OPTIMISTIC]
    [TYPE_WARNING]
    FOR <SELECT statement>
    [ FOR UPDATE [ OF <Column List>]][;]

FETCH [NEXT | PRIOR | FIRST | LAST | ABSOLUTE <Value> | RELATIVE <Value>]
FROM <Cursor Name> INTO <Variable List>;
```

### Example

```sql
DECLARE MyCursor CURSOR FOR
    SELECT *
    FROM Table1 AS T1
        INNER JOIN
        Table2 AS T2
        ON T1.Col1 = T2.Col1;
    OPEN MyCursor;
    DECLARE @VarCursor1 VARCHAR(20);
    FETCH NEXT
        FROM MyCursor INTO @VarCursor1;

    WHILE @@FETCH_STATUS = 0
    BEGIN
        EXEC MyPRocessingProcedure
            @InputParameter = @VarCursor1;
        FETCH NEXT
            FROM product_cursor INTO @VarCursor1;
    END

    CLOSE MyCursor;
    DEALLOCATE MyCursor ;
```

## MySQL

Aurora MySQL supports cursors only within stored routines (functions and stored procedures). Cursors are:
* **Asensitive** — server may copy the result table or access source directly.
* **Read-only** — not updatable.
* **Nonscrollable** — one direction only, no skipping; only `FETCH NEXT` supported.

Cursor declarations appear before handler declarations and after variable/condition declarations. No `DEALLOCATE` statement (not needed). `SELECT INTO` not allowed in a cursor. Cursors can be nested; each must have a unique name in a block.

When the cursor is exhausted, Aurora MySQL raises a no-data condition with `SQLSTATE` = `02000`. Catch it (or `NOT FOUND`) with a condition handler.

### Statements

```sql
DECLARE <Cursor Name> CURSOR FOR <Cursor SELECT Statement>
OPEN <Cursor Name>;
FETCH [[NEXT] FROM] <Cursor Name> INTO <Variable 1> [,<Variable n>];
CLOSE <Cursor Name>;
```

If a cursor isn't explicitly closed, Aurora MySQL closes it automatically at the end of the `BEGIN…END` block.

### Example — cursor loop merging into OrderItems

```sql
CREATE TABLE OrderItems
(
    OrderID INT NOT NULL,
    Item VARCHAR(20) NOT NULL,
    Quantity SMALLINT NOT NULL,
    PRIMARY KEY(OrderID, Item)
);

CREATE TABLE SourceTable
(
    OrderID INT,
    Item VARCHAR(20),
    Quantity SMALLINT,
    PRIMARY KEY (OrderID, Item)
);

INSERT INTO SourceTable (OrderID, Item, Quantity)
VALUES
(1, 'M8 Bolt', 100),
(2, 'M8 Nut', 100),
(3, 'M8 Washer', 200);

CREATE PROCEDURE LoopItems()
BEGIN
    DECLARE done INT DEFAULT FALSE;
    DECLARE var_OrderID INT;
    DECLARE var_Item VARCHAR(20);
    DECLARE var_Quantity SMALLINT;
    DECLARE ItemCursor CURSOR
    FOR
        SELECT OrderID, Item, Quantity
        FROM SourceTable;
    DECLARE CONTINUE HANDLER
        FOR NOT FOUND
        SET done = TRUE;
    OPEN ItemCursor;
    CursorStart: LOOP
    FETCH NEXT
        FROM ItemCursor
        INTO var_OrderID, var_Item, var_Quantity;
    IF Done
        THEN LEAVE CursorStart;
    END IF;
        INSERT INTO OrderItems (OrderID, Item, Quantity)
        VALUES (var_OrderID, var_Item, var_Quantity);
    END LOOP;
    CLOSE ItemCursor;
END;

CALL LoopItems();
```

## Conversion notes

- Aurora MySQL supports only static, forward-only, read-only cursors. Advanced cursor features (scrollable, keyset, dynamic, updatable `FOR UPDATE`) must be rewritten.
- Most apps use forward-only read-only cursors — these migrate easily.
- Move ad-hoc batch cursors into a stored procedure or function.
- No `DEALLOCATE` — `CLOSE` deallocates (or auto-close at end of block).
- Replace `@@FETCH_STATUS` loop control with a `CONTINUE HANDLER FOR NOT FOUND` setting a done flag.

Verified on Aurora MySQL 3.13 and 8.4.8:
- **Trap:** a `SELECT … INTO` that finds no rows raises the same NOT FOUND condition as an exhausted cursor, so inside the loop it sets `done` and ends the loop early (a 3-row cursor processed 1 row). Wrap such lookups in `BEGIN DECLARE CONTINUE HANDLER FOR NOT FOUND BEGIN END; SELECT … INTO …; END;` (then all 3 rows were processed).
- Opening an already open cursor fails with error 1325 (track open state yourself instead of `CURSOR_STATUS()`).
- Cursor parameters: reference routine parameters or local variables in the cursor's `SELECT`; they are bound at `OPEN` (verified). A cursor cannot be declared over a `PREPARE`d statement — for dynamic cursor SQL, `PREPARE` an `INSERT INTO temp_table SELECT …` and declare the cursor on the temporary table.
- `SCROLL` and option keywords (`FAST_FORWARD`, `STATIC`, …) are syntax errors (verified for `SCROLL`); remove them.
- `UPDATE … WHERE CURRENT OF c` → update by the primary key fetched from the cursor.
- `CURSOR` output parameters / `sp_cursor*` → return a result set from the procedure (a final `SELECT`).
- Most T-SQL cursor loops are row-by-row versions of set operations; replace them with `INSERT … SELECT` or multi-table `UPDATE … JOIN` when possible.

| Feature | SQL Server | Aurora MySQL | Comments |
|---|---|---|---|
| Cursor options | `[FORWARD_ONLY\|SCROLL]`, `[STATIC\|KEYSET\|DYNAMIC\|FAST_FORWARD]`, `[READ_ONLY\|SCROLL_LOCKS\|OPTIMISTIC]` | none | |
| Updateable cursors | `DECLARE CURSOR… FOR UPDATE` | Not supported | |
| Declaration | `DECLARE CURSOR` | `DECLARE CURSOR` | No options in Aurora MySQL |
| Open | `OPEN` | `OPEN` | |
| Fetch | `FETCH NEXT\|PRIOR\|FIRST\|LAST\|ABSOLUTE\|RELATIVE` | `FETCH NEXT` only | |
| Close | `CLOSE` | `CLOSE` | |
| Deallocate | `DEALLOCATE` | N/A | `CLOSE` deallocates |
| Cursor end condition | `@@FETCH_STATUS` | Event/condition handler | Handlers aren't cursor-specific |
