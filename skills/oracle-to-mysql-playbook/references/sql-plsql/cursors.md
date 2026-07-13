# Cursors

> Source: AWS Oracle→Aurora MySQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/oracle-to-aurora-mysql-migration-playbook/chap-oracle-aurora-mysql.sql.cursors.html

**Conversion category:** Assisted (★★★★ feature compatibility, ★★★ automation)
**SCT automation:** Action code "Cursors" — minor syntax rewrites; MySQL lacks `%ISOPEN`, `%ROWTYPE`, `%BULK_ROWCOUNT`.

## Oracle

PL/SQL cursors are pointers to query result sets. Two types:
* **Implicit cursors** — opened automatically by PL/SQL for each `SELECT`/DML (a.k.a. SQL cursors).
* **Explicit cursors** — user-declared and named.

```sql
-- Explicit cursor
DECLARE
  CURSOR c1 IS
    SELECT last_name, job_id FROM employees
    WHERE REGEXP_LIKE (job_id, 'S[HT]_CLERK')
    ORDER BY last_name;
    v_lastname employees.last_name%TYPE;
    v_jobid employees.job_id%TYPE;
BEGIN
  OPEN c1;
  LOOP
    FETCH c1 INTO v_lastname, v_jobid;
    EXIT WHEN c1%NOTFOUND;
  END LOOP;
  CLOSE c1;
END;

-- Implicit cursor via FOR loop
BEGIN
  FOR item IN
    (SELECT last_name, job_id FROM employees WHERE job_id LIKE '%MANAGER%'
       AND manager_id > 400 ORDER BY last_name) LOOP
    DBMS_OUTPUT.PUT_LINE('Name = ' || item.last_name || ', Job = ' || item.job_id);
  END LOOP;
END;
/
```

## MySQL

Aurora MySQL supports cursors **only inside stored routines/procedures/functions**. Characteristics: **not sensitive**, **read-only** (not updatable), **not scrollable** (forward-only, `FETCH NEXT` only). Cursor declarations must come after variable/condition declarations and before handler declarations.

```sql
DECLARE <Cursor Name> CURSOR FOR <SELECT Statement>;
OPEN <Cursor Name>;
FETCH [[NEXT] FROM] <Cursor Name> INTO <Variable 1> [,<Variable n>];
CLOSE <Cursor Name>;
```

Rules: `SELECT INTO` not allowed in a cursor; multiple cursors allowed (unique names); cursors can be nested. Exhausting the cursor raises a NO DATA / NOT FOUND condition (`SQLSTATE '02000'`) — handle with a condition handler. If not explicitly closed, MySQL closes it at the end of the `BEGIN…END` block. Number of FETCH variables must match cursor columns.

```sql
CREATE TABLE OrderItems(OrderID INT NOT NULL, Item VARCHAR(20) NOT NULL,
  Quantity SMALLINT NOT NULL, PRIMARY KEY(OrderID, Item));
CREATE TABLE SourceTable (OrderID INT, Item VARCHAR(20), Quantity SMALLINT,
  PRIMARY KEY (OrderID, Item));
INSERT INTO SourceTable VALUES (1,'M8 Bolt',100),(2,'M8 Nut',100),(3,'M8 Washer',200);

CREATE PROCEDURE LoopItems()
BEGIN
  DECLARE done INT DEFAULT FALSE;
  DECLARE var_OrderID INT;
  DECLARE var_Item VARCHAR(20);
  DECLARE var_Quantity SMALLINT;
  DECLARE ItemCursor CURSOR FOR SELECT OrderID, Item, Quantity FROM SourceTable;
  DECLARE CONTINUE HANDLER FOR NOT FOUND SET done = TRUE;
  OPEN ItemCursor;
  CursorStart: LOOP
    FETCH NEXT FROM ItemCursor INTO var_OrderID, var_Item, var_Quantity;
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

| Action | Oracle | Aurora MySQL |
|---|---|---|
| Declare explicit cursor | `CURSOR c1 IS SELECT ...` | `DECLARE c1 CURSOR FOR SELECT ...` |
| Open | `OPEN c1;` | `OPEN c1;` |
| Fetch into record | `FETCH c1 INTO rowvar;` | `FETCH NEXT FROM c1 INTO rowvar;` |
| Fetch into scalars | `FETCH c1 INTO a,b,c;` | `FETCH NEXT FROM c1 INTO a,b,c;` |
| Implicit cursor FOR loop | `FOR item IN (SELECT ...) LOOP` | N/A — use explicit cursor + loop |
| Parameterized cursor | `CURSOR c1 (key NUMBER) IS ...; OPEN c1(2);` | Build with `CONCAT` + `PREPARE`/`EXECUTE` dynamic SQL, then `OPEN` |
| Exit on no data | `EXIT WHEN c1%NOTFOUND;` | `DECLARE CONTINUE HANDLER FOR NOT FOUND SET done=TRUE;` + `IF done THEN LEAVE;` |
| `%FOUND` | yes | N/A |
| `%BULK_ROWCOUNT` | yes | use counters |
| `%BULK_EXCEPTIONS` | yes | N/A |
| `%ISOPEN` | yes | N/A |
| `%NOTFOUND` | yes | NOT FOUND handler |
| `%ROWCOUNT` | yes | N/A |

- Wrap each cursor in its own `BEGIN…END` block so its NOT FOUND handler doesn't catch conditions from other statements.
- Replace Oracle cursor attributes (`%FOUND`, `%ROWCOUNT`, `%ISOPEN`, etc.) with handler flags and manual counters.
- Parameterized cursors require dynamic SQL (`PREPARE`/`EXECUTE`).
