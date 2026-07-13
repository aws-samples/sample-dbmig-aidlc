# User-defined types for T-SQL

> Source: AWS SQL Server→Aurora MySQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/sql-server-to-aurora-mysql-migration-playbook/chap-sql-server-aurora-mysql.tsql.udt.html

**Conversion category:** Manual (Three star feature compatibility)
**SCT automation:** Three star automation level

## SQL Server

User-defined types encapsulate custom data types and add NULL constraints; all based on existing system types. SQL Server also supports table-valued UDTs for passing a set of values to a stored procedure, and CLR-associated types. Memory-optimized types (2014+) support memory-optimized tables.

### Syntax

```sql
CREATE TYPE <type name> {
FROM <base type> [ NULL | NOT NULL ] | AS TABLE (<Table Definition>)}
```

### Examples

```sql
-- scalar UDT
CREATE TYPE ZipCode
FROM CHAR(5)
NOT NULL;

CREATE TABLE UserLocations
(UserID INT NOT NULL PRIMARY KEY, ZipCode ZipCode);

-- table-valued type passed to a procedure
CREATE TYPE OrderItems
AS TABLE
(
    OrderID INT NOT NULL,
    Item VARCHAR(20) NOT NULL,
    Quantity SMALLINT NOT NULL,
    PRIMARY KEY(OrderID, Item)
);

CREATE PROCEDURE InsertOrderItems
@OrderItems AS OrderItems READONLY
AS
BEGIN
    INSERT INTO OrderItems(OrderID, Item, Quantity)
    SELECT OrderID, Item, Quantity
    FROM @OrderItems;
END

DECLARE @OrderItems AS OrderItems;
INSERT INTO @OrderItems ([OrderID], [Item], [Quantity])
VALUES (1, 'M8 Bolt', 100), (1, 'M8 Nut', 100), (1, 'M8 Washer', 200);
EXECUTE [InsertOrderItems] @OrderItems = @OrderItems;
```

## MySQL

Aurora MySQL 5.7 does **not** support user-defined types or table-valued parameters (no indication of support in version 8). Memory-optimized engines are also unsupported.

### Examples

```sql
-- Replace scalar UDT with the base type
CREATE TABLE UserLocations
(
    UserID INT NOT NULL PRIMARY KEY,
    /*ZipCode*/ CHAR(5) NOT NULL
);

-- Replace table-valued parameter with a source table + LOOP cursor
CREATE TABLE OrderItems
(
    OrderID INT NOT NULL,
    Item VARCHAR(20) NOT NULL,
    Quantity SMALLINT NOT NULL,
    PRIMARY KEY(OrderID, Item)
);

CREATE PROCEDURE LoopItems()
BEGIN
    DECLARE done INT DEFAULT FALSE;
    DECLARE var_OrderID INT;
    DECLARE var_Item VARCHAR(20);
    DECLARE var_Quantity SMALLINT;
    DECLARE ItemCursor CURSOR
        FOR SELECT OrderID, Item, Quantity FROM SourceTable;
    DECLARE CONTINUE HANDLER
        FOR NOT FOUND SET done = TRUE;
    OPEN ItemCursor;
    CursorStart: LOOP
    FETCH NEXT FROM ItemCursor
        INTO var_OrderID, var_Item, var_Quantity;
    IF Done THEN LEAVE CursorStart;
    END IF;
        INSERT INTO OrderItems (OrderID, Item, Quantity)
        VALUES (var_OrderID, var_Item, var_Quantity);
    END LOOP;
    CLOSE ItemCursor;
END;

CALL LoopItems();
```

## Conversion notes

- Scalar UDT → replace the type name with its base type plus optional NULL/NOT NULL constraints.
- Table-valued UDT parameter → workarounds: temporary tables to hold data; or pass CSV/XML/JSON string parameters and parse them in the procedure; or for small sets, call the procedure row-by-row with standard parameters.
- Memory-optimized tables → convert to disk-based tables.

| SQL Server | Aurora MySQL | Comments |
|---|---|---|
| Scalar UDT | Not supported | Use base type + NULL constraint |
| Table-valued parameters | Not supported | Temp tables, CSV/XML/JSON strings, or row-by-row loop |
| Memory-optimized table-valued UDTs | Not supported | Convert to disk-based tables |
