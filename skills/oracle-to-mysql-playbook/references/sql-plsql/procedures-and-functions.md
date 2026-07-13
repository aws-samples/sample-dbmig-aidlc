# Procedures and Functions

> Source: AWS Oracle→Aurora MySQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/oracle-to-aurora-mysql-migration-playbook/chap-oracle-aurora-mysql.sql.stored.html

**Conversion category:** Assisted (★★★ feature compatibility, ★★★★ automation)
**SCT automation:** Action code "Stored Procedures" — syntax and option differences.

## Oracle

PL/SQL procedures (`CREATE PROCEDURE`, perform actions) and functions (`CREATE FUNCTION`, return a value) store reusable logic. Privileges: `CREATE PROCEDURE` (own schema), `CREATE ANY PROCEDURE` (other schemas), `EXECUTE` (to run). **Packages** (`CREATE PACKAGE` + `CREATE PACKAGE BODY`) encapsulate related routines; call as `EXEC PKG.PROC(...)`.

```sql
-- Procedure
CREATE OR REPLACE PROCEDURE EMP_SAL_RAISE (P_EMP_ID IN NUMBER, SAL_RAISE IN NUMBER)
AS
  V_EMP_CURRENT_SAL NUMBER;
BEGIN
  SELECT SALARY INTO V_EMP_CURRENT_SAL FROM EMPLOYEES WHERE EMPLOYEE_ID=P_EMP_ID;
  UPDATE EMPLOYEES SET SALARY=V_EMP_CURRENT_SAL+SAL_RAISE WHERE EMPLOYEE_ID=P_EMP_ID;
  DBMS_OUTPUT.PUT_LINE('New Salary For Employee ID: '||P_EMP_ID||' Is '||(V_EMP_CURRENT_SAL+SAL_RAISE));
EXCEPTION WHEN OTHERS THEN
  RAISE_APPLICATION_ERROR(-20001,'An error was encountered - '||SQLCODE||' -ERROR-'||SQLERRM);
  ROLLBACK;
  COMMIT;
END;
/
EXEC EMP_SAL_RAISE(200, 1000);

-- Function
CREATE OR REPLACE FUNCTION EMP_PERIOD_OF_SERVICE_YEAR (P_EMP_ID NUMBER)
RETURN NUMBER
AS
  V_PERIOD_OF_SERVICE_YEARS NUMBER;
BEGIN
  SELECT EXTRACT(YEAR FROM SYSDATE) - EXTRACT(YEAR FROM TO_DATE(HIRE_DATE))
    INTO V_PERIOD_OF_SERVICE_YEARS
  FROM EMPLOYEES WHERE EMPLOYEE_ID=P_EMP_ID;
  RETURN V_PERIOD_OF_SERVICE_YEARS;
END;
/

-- Package + body
CREATE OR REPLACE PACKAGE PCK_CHINOOK_REPORTS AS
  PROCEDURE GET_ARTIST_BY_ALBUM(P_ARTIST_ID ALBUM.TITLE%TYPE);
  PROCEDURE CUST_INVOICE_BY_YEAR_ANALYZE;
END;

CREATE OR REPLACE PACKAGE BODY PCK_CHINOOK_REPORTS AS
  PROCEDURE GET_ARTIST_BY_ALBUM(P_ARTIST_ID ALBUM.TITLE%TYPE) IS ... END;
  PROCEDURE CUST_INVOICE_BY_YEAR_ANALYZE AS ... END;
END;
EXEC PCK_CHINOOK_REPORTS.GET_ARTIST_BY_ALBUM();
```

## MySQL

Aurora MySQL stored procedures provide similar functionality, including security execution context and `IN`/`OUT`/`INOUT` parameters. Used for code reuse, security management (access via procedures only), and performance (no full query text transferred). Stored procedures, triggers, and UDFs are collectively **Stored Routines**.

> Note: With binary logging enabled, running stored routines requires `SUPER` privilege, or set `log_bin_trust_function_creators=true` on the DB parameter group. Routines may contain control flow, DML, DDL, and `START TRANSACTION`/`COMMIT`/`ROLLBACK`.

```sql
-- Syntax
CREATE [DEFINER = { user | CURRENT_USER }] PROCEDURE sp_name ([proc_parameter[,...]])
  [characteristic ...] routine_body
  proc_parameter: [ IN | OUT | INOUT ] param_name type
  characteristic: COMMENT 'string' | LANGUAGE SQL | [NOT] DETERMINISTIC
    | { CONTAINS SQL | NO SQL | READS SQL DATA | MODIFIES SQL DATA }
    | SQL SECURITY { DEFINER | INVOKER }

-- Cursor-loop procedure (replaces table-valued parameters)
CREATE TABLE OrderItems(OrderID INT NOT NULL, Item VARCHAR(20) NOT NULL,
  Quantity SMALLINT NOT NULL, PRIMARY KEY(OrderID, Item));
CREATE TABLE SourceTable (OrderID INT, Item VARCHAR(20), Quantity SMALLINT,
  PRIMARY KEY (OrderID, Item));
INSERT INTO SourceTable VALUES (1,'M8 Bolt',100),(2,'M8 Nut',100),(3,'M8 Washer',200);

CREATE PROCEDURE LoopItems()
BEGIN
  DECLARE done INT DEFAULT FALSE;
  DECLARE var_OrderID INT; DECLARE var_Item VARCHAR(20); DECLARE var_Quantity SMALLINT;
  DECLARE ItemCursor CURSOR FOR SELECT OrderID, Item, Quantity FROM SourceTable;
  DECLARE CONTINUE HANDLER FOR NOT FOUND SET done = TRUE;
  OPEN ItemCursor;
  CursorStart: LOOP
    FETCH NEXT FROM ItemCursor INTO var_OrderID, var_Item, var_Quantity;
    IF Done THEN LEAVE CursorStart; END IF;
    INSERT INTO OrderItems (OrderID, Item, Quantity) VALUES (var_OrderID, var_Item, var_Quantity);
  END LOOP;
  CLOSE ItemCursor;
END;
CALL LoopItems();
```

## Conversion notes

| | Oracle | Aurora MySQL | Workaround |
|---|---|---|---|
| CREATE syntax | `CREATE PROCEDURE name Param1 Type,...n AS <Body>` | `CREATE PROCEDURE name (Param1 Type,...n) <Body>` | Use `PROCEDURE` (not `PROC`); omit `AS`; parenthesize params |
| Security context | `AUTHID { CURRENT_USER \| DEFINER }` | `DEFINER='user'\|CURRENT_USER` + `SQL SECURITY {DEFINER\|INVOKER}` | `EXECUTE AS 'user'`→`DEFINER='user'`+`SQL SECURITY DEFINER`; `CALLER`→`SQL SECURITY INVOKER`; `SELF`→`DEFINER=CURRENT_USER`+`SQL SECURITY DEFINER` |
| Parameter direction | `IN`, `OUT` (OUT usable as IN) | `IN`, `OUT`, `INOUT` | |

- **No packages** in MySQL — flatten package procedures/functions into standalone routines (e.g., `PKG_PROC` naming) and convert package-level state to tables/variables.
- Replace `DBMS_OUTPUT.PUT_LINE` with `SELECT`; replace `RAISE_APPLICATION_ERROR` with `SIGNAL SQLSTATE`.
- Functions: use `CREATE FUNCTION ... RETURNS <type>` with characteristics; mark `DETERMINISTIC`/`READS SQL DATA` as needed.
