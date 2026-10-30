<!-- dbmig test-generation prompt  batch 1/5
     Write one test spec (YAML) per object:
       - FUNCTION DBO.ufnCalculateCustomerLifetimeValue -> tests/DBO/function__ufncalculatecustomerlifetimevalue.test.yaml
       - FUNCTION DBO.ufnGetAccountingEndDate -> tests/DBO/function__ufngetaccountingenddate.test.yaml
       - FUNCTION DBO.ufnGetAccountingStartDate -> tests/DBO/function__ufngetaccountingstartdate.test.yaml
       - FUNCTION DBO.ufnGetDocumentStatusText -> tests/DBO/function__ufngetdocumentstatustext.test.yaml
       - FUNCTION DBO.ufnGetPurchaseOrderStatusText -> tests/DBO/function__ufngetpurchaseorderstatustext.test.yaml
       - FUNCTION DBO.ufnGetSalesOrderStatusText -> tests/DBO/function__ufngetsalesorderstatustext.test.yaml
     Then set each unit's status 'generated' in test-manifest-DBO.yaml. -->

=== CONTEXT ===
Shared tests context for this run: `migrations/<project>/03-validation/_context-tests.md`. Read it once per session if you have not already — it holds the customer-specific rules (highest precedence), datatype map, engine checks and playbook index this task relies on. Do not skip it.

=== TASK — GENERATE EQUIVALENCE TESTS ===
Generate equivalence tests that prove each of the 6 converted PostgreSQL (Aurora PostgreSQL compatible) objects below (one spec file per object, as listed in the header) behaves the same as the SQL Server source: same input → same return value (functions) or same net effect (procedures). Tests run on BOTH engines and the results are compared. Use the spec format and Rules in the context above.

### FUNCTION DBO.ufnCalculateCustomerLifetimeValue — write a **function**-shape spec
--- SOURCE (FUNCTION) — DBO.ufnCalculateCustomerLifetimeValue ---
CREATE   FUNCTION [dbo].[ufnCalculateCustomerLifetimeValue]
(
    @CustomerID INT
)
RETURNS DECIMAL(10, 2)
AS
BEGIN
    DECLARE @TotalSpent DECIMAL(10, 2);
    DECLARE @FirstOrderDate DATE;
    DECLARE @DaysSinceFirstOrder INT;
    DECLARE @LifetimeValue DECIMAL(10, 2);
    
    SELECT 
        @TotalSpent = SUM([TotalAmount]),
        @FirstOrderDate = MIN([OrderDate])
    FROM [dbo].[Shopping]
    WHERE [CustomerID] = @CustomerID AND TRIM([Status]) != 'Refund Requested';
    
    SET @DaysSinceFirstOrder = DATEDIFF(DAY, @FirstOrderDate, GETDATE());
    
    IF @DaysSinceFirstOrder = 0
        SET @LifetimeValue = @TotalSpent;
    ELSE
        SET @LifetimeValue = (@TotalSpent / @DaysSinceFirstOrder) * 365.25;
    
    RETURN @LifetimeValue;
END;

--- CONVERTED TARGET CODE (PostgreSQL) — use these exact routine names and signatures in target_sql / call_target ---
-- DECIMAL(10,2) locals: every assignment rounds to 2 dp, as in SQL Server.
-- DATEDIFF(DAY, d, GETDATE()) counts day boundaries = current_date - d::date.
CREATE OR REPLACE FUNCTION dbo.ufncalculatecustomerlifetimevalue(p_customerid integer)
RETURNS numeric(10,2) LANGUAGE plpgsql STABLE AS $$
DECLARE
    v_totalspent numeric(10,2);
    v_firstorderdate date;
    v_days integer;
    v_lifetimevalue numeric(10,2);
BEGIN
    SELECT sum(totalamount), min(orderdate)::date INTO v_totalspent, v_firstorderdate
    FROM dbo.shopping
    WHERE customerid = p_customerid AND trim(status) <> 'Refund Requested';
    v_days := current_date - v_firstorderdate;
    IF v_days = 0 THEN
        v_lifetimevalue := v_totalspent;
    ELSE
        v_lifetimevalue := (v_totalspent / v_days) * 365.25;
    END IF;
    RETURN v_lifetimevalue;
END $$;

### FUNCTION DBO.ufnGetAccountingEndDate — write a **function**-shape spec
--- SOURCE (FUNCTION) — DBO.ufnGetAccountingEndDate ---
CREATE FUNCTION [dbo].[ufnGetAccountingEndDate]()
RETURNS [datetime] 
AS 
BEGIN
    RETURN DATEADD(millisecond, -2, CONVERT(datetime, '20040701', 112));
END;

--- CONVERTED TARGET CODE (PostgreSQL) — use these exact routine names and signatures in target_sql / call_target ---
-- SQL Server datetime has 1/300 s ticks: DATEADD(ms,-2,'2004-07-01') rounds to 23:59:59.997.
-- PostgreSQL timestamps are exact, so the rounded value is reproduced explicitly (checklist item 8).
CREATE OR REPLACE FUNCTION dbo.ufngetaccountingenddate()
RETURNS timestamp(3) LANGUAGE sql IMMUTABLE AS $$
    SELECT timestamp '2004-06-30 23:59:59.997'
$$;

### FUNCTION DBO.ufnGetAccountingStartDate — write a **function**-shape spec
--- SOURCE (FUNCTION) — DBO.ufnGetAccountingStartDate ---
CREATE FUNCTION [dbo].[ufnGetAccountingStartDate]()
RETURNS [datetime] 
AS 
BEGIN
    RETURN CONVERT(datetime, '20030701', 112);
END;

--- CONVERTED TARGET CODE (PostgreSQL) — use these exact routine names and signatures in target_sql / call_target ---
CREATE OR REPLACE FUNCTION dbo.ufngetaccountingstartdate()
RETURNS timestamp(3) LANGUAGE sql IMMUTABLE AS $$
    SELECT timestamp '2003-07-01 00:00:00'
$$;

### FUNCTION DBO.ufnGetDocumentStatusText — write a **function**-shape spec
--- SOURCE (FUNCTION) — DBO.ufnGetDocumentStatusText ---
CREATE FUNCTION [dbo].[ufnGetDocumentStatusText](@Status [tinyint])
RETURNS [nvarchar](16) 
AS 
BEGIN
    DECLARE @ret [nvarchar](16);

    SET @ret = 
        CASE @Status
            WHEN 1 THEN N'Pending approval'
            WHEN 2 THEN N'Approved'
            WHEN 3 THEN N'Obsolete'
            ELSE N'** Invalid **'
        END;
    
    RETURN @ret
END;

--- CONVERTED TARGET CODE (PostgreSQL) — use these exact routine names and signatures in target_sql / call_target ---
-- tinyint (0-255) -> integer parameter: a smallint parameter does not resolve for callers passing an
-- integer literal (PostgreSQL will not implicitly narrow integer -> smallint in function lookup).
CREATE OR REPLACE FUNCTION dbo.ufngetdocumentstatustext(p_status integer)
RETURNS varchar(16) LANGUAGE sql IMMUTABLE AS $$
    SELECT CASE p_status WHEN 1 THEN 'Pending approval' WHEN 2 THEN 'Approved' WHEN 3 THEN 'Obsolete' ELSE '** Invalid **' END::varchar(16)
$$;

### FUNCTION DBO.ufnGetPurchaseOrderStatusText — write a **function**-shape spec
--- SOURCE (FUNCTION) — DBO.ufnGetPurchaseOrderStatusText ---
CREATE FUNCTION [dbo].[ufnGetPurchaseOrderStatusText](@Status [tinyint])
RETURNS [nvarchar](15) 
AS 
BEGIN
    DECLARE @ret [nvarchar](15);

    SET @ret = 
        CASE @Status
            WHEN 1 THEN 'Pending'
            WHEN 2 THEN 'Approved'
            WHEN 3 THEN 'Rejected'
            WHEN 4 THEN 'Complete'
            ELSE '** Invalid **'
        END;
    
    RETURN @ret
END;

--- CONVERTED TARGET CODE (PostgreSQL) — use these exact routine names and signatures in target_sql / call_target ---
-- tinyint (0-255) -> integer parameter: a smallint parameter does not resolve for callers passing an
-- integer literal (PostgreSQL will not implicitly narrow integer -> smallint in function lookup).
CREATE OR REPLACE FUNCTION dbo.ufngetpurchaseorderstatustext(p_status integer)
RETURNS varchar(15) LANGUAGE sql IMMUTABLE AS $$
    SELECT CASE p_status WHEN 1 THEN 'Pending' WHEN 2 THEN 'Approved' WHEN 3 THEN 'Rejected' WHEN 4 THEN 'Complete' ELSE '** Invalid **' END::varchar(15)
$$;

### FUNCTION DBO.ufnGetSalesOrderStatusText — write a **function**-shape spec
--- SOURCE (FUNCTION) — DBO.ufnGetSalesOrderStatusText ---
CREATE FUNCTION [dbo].[ufnGetSalesOrderStatusText](@Status [tinyint])
RETURNS [nvarchar](15) 
AS 
BEGIN
    DECLARE @ret [nvarchar](15);

    SET @ret = 
        CASE @Status
            WHEN 1 THEN 'In process'
            WHEN 2 THEN 'Approved'
            WHEN 3 THEN 'Backordered'
            WHEN 4 THEN 'Rejected'
            WHEN 5 THEN 'Shipped'
            WHEN 6 THEN 'Cancelled'
            ELSE '** Invalid **'
        END;
    
    RETURN @ret
END;

--- CONVERTED TARGET CODE (PostgreSQL) — use these exact routine names and signatures in target_sql / call_target ---
-- tinyint (0-255) -> integer parameter: a smallint parameter does not resolve for callers passing an
-- integer literal (PostgreSQL will not implicitly narrow integer -> smallint in function lookup).
CREATE OR REPLACE FUNCTION dbo.ufngetsalesorderstatustext(p_status integer)
RETURNS varchar(15) LANGUAGE sql IMMUTABLE AS $$
    SELECT CASE p_status WHEN 1 THEN 'In process' WHEN 2 THEN 'Approved' WHEN 3 THEN 'Backordered' WHEN 4 THEN 'Rejected' WHEN 5 THEN 'Shipped' WHEN 6 THEN 'Cancelled' ELSE '** Invalid **' END::varchar(15)
$$;

--- SAMPLED REAL DATA (use these actual values) ---
### Shopping  (columns: OrderID, CustomerID, OrderDate, TotalAmount, Status)
  1 | 1 | 2022-01-10 00:00:00 | 100 | Delivered
  2 | 2 | 2022-02-20 00:00:00 | 75.5 | Shipped
  3 | 3 | 2022-03-25 00:00:00 | 200.75 | Processing
