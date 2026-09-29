<!-- dbmig test-generation prompt  batch 5/5
     Write one test spec (YAML) per object:
       - PROCEDURE DBO.uspProcessRefunds -> tests/DBO/procedure__uspprocessrefunds.test.yaml
       - PROCEDURE DBO.uspShoppingLevelAmount -> tests/DBO/procedure__uspshoppinglevelamount.test.yaml
       - PROCEDURE DBO.uspUpdateAuthorLogin -> tests/DBO/procedure__uspupdateauthorlogin.test.yaml
       - PROCEDURE DBO.uspUpdateAuthorPersonalInfo -> tests/DBO/procedure__uspupdateauthorpersonalinfo.test.yaml
     Then set each unit's status 'generated' in test-manifest-DBO.yaml. -->

=== CONTEXT ===
Shared tests context for this run: `migrations/<project>/03-validation/_context-tests.md`. Read it once per session if you have not already — it holds the customer-specific rules (highest precedence), datatype map, engine checks and playbook index this task relies on. Do not skip it.

=== TASK — GENERATE EQUIVALENCE TESTS ===
Generate equivalence tests that prove each of the 4 converted PostgreSQL (Aurora PostgreSQL compatible) objects below (one spec file per object, as listed in the header) behaves the same as the SQL Server source: same input → same return value (functions) or same net effect (procedures). Tests run on BOTH engines and the results are compared. Use the spec format and Rules in the context above.

### PROCEDURE DBO.uspProcessRefunds — write a **procedure**-shape spec
--- SOURCE (PROCEDURE) — DBO.uspProcessRefunds ---
CREATE   PROCEDURE [dbo].[uspProcessRefunds]
AS
BEGIN
    SET NOCOUNT ON;

    DECLARE @RefundCount INT = 0;
    DECLARE @MaxID INT;

    SELECT @MaxID = MAX([TicketID]) FROM [dbo].[Coupons];
    
    SELECT [OrderID], [CustomerID], [TotalAmount]
    INTO #RefundRequests
    FROM [dbo].[Shopping]
    WHERE TRIM([Status]) = 'Refund Requested';
    
    UPDATE o
    SET [Status] = 'Refunded'
    FROM [dbo].[Shopping] o
    INNER JOIN #RefundRequests r ON o.[OrderID] = r.[OrderID];
    
    INSERT INTO [dbo].[Coupons] ([TicketID], [CustomerID], [OrderID], [IssueDescription], [CreatedDate], [Status])
    SELECT 
        @MaxID + ROW_NUMBER() OVER (ORDER BY [OrderID]),
        [CustomerID],
        [OrderID],
        'Refund processed for $' + CAST([TotalAmount] AS NVARCHAR(20)),
        GETDATE(),
        'Closed'
    FROM #RefundRequests;

    SET @RefundCount = @@ROWCOUNT;

    PRINT 'Processed ' + CAST(@RefundCount AS NVARCHAR(10)) + ' refunds.';

    DROP TABLE #RefundRequests;
END;

--- CONVERTED TARGET CODE (PostgreSQL) — use these exact routine names and signatures in target_sql / call_target ---
-- #RefundRequests temp table -> data-modifying CTE: the key set is read once (same snapshot) and
-- used by both the UPDATE and the INSERT, exactly as the temp table was. @@ROWCOUNT after the
-- INSERT -> GET DIAGNOSTICS. GETDATE() -> localtimestamp. CAST(x AS NVARCHAR(20)) -> x::varchar(20).
CREATE OR REPLACE PROCEDURE dbo.uspprocessrefunds()
LANGUAGE plpgsql AS $$
DECLARE
    v_refundcount integer := 0;
    v_maxid integer;
BEGIN
    SELECT max(ticketid) INTO v_maxid FROM dbo.coupons;
    WITH r AS (
        SELECT orderid, customerid, totalamount FROM dbo.shopping WHERE trim(status) = 'Refund Requested'
    ), u AS (
        UPDATE dbo.shopping o SET status = 'Refunded' FROM r WHERE o.orderid = r.orderid
    )
    INSERT INTO dbo.coupons (ticketid, customerid, orderid, issuedescription, createddate, status)
    SELECT v_maxid + row_number() OVER (ORDER BY orderid), customerid, orderid,
           'Refund processed for $' || totalamount::varchar(20), localtimestamp, 'Closed'
    FROM r;
    GET DIAGNOSTICS v_refundcount = ROW_COUNT;
    RAISE NOTICE 'Processed % refunds.', v_refundcount;
END $$;

### PROCEDURE DBO.uspShoppingLevelAmount — write a **procedure**-shape spec
--- SOURCE (PROCEDURE) — DBO.uspShoppingLevelAmount ---
CREATE   PROCEDURE [dbo].[uspShoppingLevelAmount]
    @Percent INT,
    @Amount NUMERIC
AS
BEGIN
    SELECT 
        [OrderID],
        '|' + CASE 
                WHEN @Percent > 100 THEN
                    CASE 
                        WHEN [TotalAmount] > @Amount THEN 'more than'
                        ELSE 'less than'
                    END
              END + '|' AS [AmountLevel]
    FROM [dbo].[Shopping];
END;

--- CONVERTED TARGET CODE (PostgreSQL) — use these exact routine names and signatures in target_sql / call_target ---
-- Result-set procedure -> set-returning FUNCTION.
-- @Amount NUMERIC defaults to numeric(18,0) in SQL Server: the argument is ROUNDED to an integer
-- on the way in — reproduced with round(). '|' + NULL + '|' is NULL in both engines.
CREATE OR REPLACE FUNCTION dbo.uspshoppinglevelamount(p_percent integer, p_amount numeric)
RETURNS TABLE (orderid integer, amountlevel text)
LANGUAGE sql STABLE AS $$
    SELECT s.orderid,
           '|' || CASE WHEN p_percent > 100 THEN
                        CASE WHEN s.totalamount > round(p_amount) THEN 'more than' ELSE 'less than' END
                  END || '|'
    FROM dbo.shopping s
$$;

### PROCEDURE DBO.uspUpdateAuthorLogin — write a **procedure**-shape spec
--- SOURCE (PROCEDURE) — DBO.uspUpdateAuthorLogin ---
CREATE PROCEDURE [dbo].[uspUpdateAuthorLogin]
    @BusinessEntityID [int], 
    @OrganizationNode [nvarchar](4000), 
    @LoginID [nvarchar](256),
    @JobTitle [nvarchar](50),
    @HireDate [datetime],
    @CurrentFlag [dbo].[Flag]
WITH EXECUTE AS CALLER
AS
BEGIN
    SET NOCOUNT ON;

    BEGIN TRY
        UPDATE [dbo].[Author] 
        SET [OrganizationNode] = @OrganizationNode 
            ,[LoginID] = @LoginID 
            ,[JobTitle] = @JobTitle 
            ,[HireDate] = @HireDate 
            ,[CurrentFlag] = @CurrentFlag 
        WHERE [BusinessEntityID] = @BusinessEntityID;
    END TRY
    BEGIN CATCH
        EXECUTE [dbo].[uspLogError];
    END CATCH;
END;

--- CONVERTED TARGET CODE (PostgreSQL) — use these exact routine names and signatures in target_sql / call_target ---
-- TRY/CATCH (error logged and swallowed) -> EXCEPTION WHEN OTHERS: the block's update is undone,
-- the error is logged via dbo.usplogerror (parameters, not ambient ERROR_*()) and NOT re-raised —
-- same observable result as SQL Server. datetime param into a date column truncates in both.
CREATE OR REPLACE PROCEDURE dbo.uspupdateauthorlogin(p_businessentityid integer, p_organizationnode varchar(4000), p_loginid varchar(256), p_jobtitle varchar(50), p_hiredate timestamp(3), p_currentflag boolean)
LANGUAGE plpgsql AS $$
DECLARE
    v_msg text; v_state text; v_id integer;
BEGIN
    UPDATE dbo.author SET organizationnode = p_organizationnode, loginid = p_loginid, jobtitle = p_jobtitle, hiredate = p_hiredate::date, currentflag = p_currentflag WHERE businessentityid = p_businessentityid;
EXCEPTION WHEN OTHERS THEN
    GET STACKED DIAGNOSTICS v_msg = MESSAGE_TEXT, v_state = RETURNED_SQLSTATE;
    CALL dbo.usplogerror(v_id, 0, 16, 1, 'uspUpdateAuthorLogin', NULL, v_state || ': ' || v_msg);
END $$;

### PROCEDURE DBO.uspUpdateAuthorPersonalInfo — write a **procedure**-shape spec
--- SOURCE (PROCEDURE) — DBO.uspUpdateAuthorPersonalInfo ---
CREATE PROCEDURE [dbo].[uspUpdateAuthorPersonalInfo]
    @BusinessEntityID [int], 
    @NationalIDNumber [nvarchar](15), 
    @BirthDate [datetime], 
    @MaritalStatus [nchar](1), 
    @Gender [nchar](1)
WITH EXECUTE AS CALLER
AS
BEGIN
    SET NOCOUNT ON;

    BEGIN TRY
        UPDATE [dbo].[Author] 
        SET [NationalIDNumber] = @NationalIDNumber 
            ,[BirthDate] = @BirthDate 
            ,[MaritalStatus] = @MaritalStatus 
            ,[Gender] = @Gender 
        WHERE [BusinessEntityID] = @BusinessEntityID;
    END TRY
    BEGIN CATCH
        EXECUTE [dbo].[uspLogError];
    END CATCH;
END;

--- CONVERTED TARGET CODE (PostgreSQL) — use these exact routine names and signatures in target_sql / call_target ---
-- TRY/CATCH (error logged and swallowed) -> EXCEPTION WHEN OTHERS: the block's update is undone,
-- the error is logged via dbo.usplogerror (parameters, not ambient ERROR_*()) and NOT re-raised —
-- same observable result as SQL Server. datetime param into a date column truncates in both.
CREATE OR REPLACE PROCEDURE dbo.uspupdateauthorpersonalinfo(p_businessentityid integer, p_nationalidnumber varchar(15), p_birthdate timestamp(3), p_maritalstatus char(1), p_gender char(1))
LANGUAGE plpgsql AS $$
DECLARE
    v_msg text; v_state text; v_id integer;
BEGIN
    UPDATE dbo.author SET nationalidnumber = p_nationalidnumber, birthdate = p_birthdate::date, maritalstatus = p_maritalstatus, gender = p_gender WHERE businessentityid = p_businessentityid;
EXCEPTION WHEN OTHERS THEN
    GET STACKED DIAGNOSTICS v_msg = MESSAGE_TEXT, v_state = RETURNED_SQLSTATE;
    CALL dbo.usplogerror(v_id, 0, 16, 1, 'uspUpdateAuthorPersonalInfo', NULL, v_state || ': ' || v_msg);
END $$;

--- SAMPLED REAL DATA (use these actual values) ---
### Coupons  (columns: TicketID, CustomerID, OrderID, IssueDescription, CreatedDate, ResolvedDate, Status, OSUser)
  1 | 1 | 1 | Item was damaged during shipping | 2022-01-15 00:00:00 | 2022-01-20 00:00:00 | Closed | sqladmin
  2 | 2 | 2 | Order not received yet | 2022-02-25 00:00:00 |  | Open | sqladmin
  3 | 3 | 3 | Wrong item shipped | 2022-03-28 00:00:00 | 2022-04-01 00:00:00 | Closed | sqladmin
### Shopping  (columns: OrderID, CustomerID, OrderDate, TotalAmount, Status)
  1 | 1 | 2022-01-10 00:00:00 | 100 | Delivered
  2 | 2 | 2022-02-20 00:00:00 | 75.5 | Shipped
  3 | 3 | 2022-03-25 00:00:00 | 200.75 | Processing
### Author  (columns: BusinessEntityID, NationalIDNumber, LoginID, OrganizationNode, JobTitle, BirthDate, MaritalStatus, Gender, HireDate, VacationHours, CurrentFlag, ModifiedDate)
  1 | 295847284 | adventure-works\ken0 |  | Chief Executive Officer | 1969-01-29 | S | M | 2009-01-14 | 99 | True | 2014-06-30 00:00:00
  2 | 245797967 | adventure-works\terri0 | 58 | Vice President of Engineering | 1971-08-01 | S | F | 2008-01-31 | 1 | True | 2014-06-30 00:00:00
  3 | 509647174 | adventure-works\roberto0 | 5AC0 | Engineering Manager | 1974-11-12 | M | M | 2007-11-11 | 2 | True | 2014-06-30 00:00:00
