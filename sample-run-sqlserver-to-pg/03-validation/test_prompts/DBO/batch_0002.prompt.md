<!-- dbmig test-generation prompt  batch 2/5
     Write one test spec (YAML) per object:
       - FUNCTION DBO.ufnLeadingZeros -> tests/DBO/function__ufnleadingzeros.test.yaml
       - VIEW DBO.VwCustomerShopping -> tests/DBO/view__vwcustomershopping.test.yaml
       - VIEW DBO.VwOpenCoupons -> tests/DBO/view__vwopencoupons.test.yaml
       - VIEW DBO.VwRegionalSales -> tests/DBO/view__vwregionalsales.test.yaml
       - VIEW DBO.VwTopMembers -> tests/DBO/view__vwtopmembers.test.yaml
       - PROCEDURE DBO.uspDeleteAuthor -> tests/DBO/procedure__uspdeleteauthor.test.yaml
     Then set each unit's status 'generated' in test-manifest-DBO.yaml. -->

=== CONTEXT ===
Shared tests context for this run: `migrations/<project>/03-validation/_context-tests.md`. Read it once per session if you have not already — it holds the customer-specific rules (highest precedence), datatype map, engine checks and playbook index this task relies on. Do not skip it.

=== TASK — GENERATE EQUIVALENCE TESTS ===
Generate equivalence tests that prove each of the 6 converted PostgreSQL (Aurora PostgreSQL compatible) objects below (one spec file per object, as listed in the header) behaves the same as the SQL Server source: same input → same return value (functions) or same net effect (procedures). Tests run on BOTH engines and the results are compared. Use the spec format and Rules in the context above.

### FUNCTION DBO.ufnLeadingZeros — write a **function**-shape spec
--- SOURCE (FUNCTION) — DBO.ufnLeadingZeros ---
CREATE FUNCTION [dbo].[ufnLeadingZeros](
    @Value int
) 
RETURNS varchar(8) 
WITH SCHEMABINDING 
AS 
BEGIN
    DECLARE @ReturnValue varchar(8);

    SET @ReturnValue = CONVERT(varchar(8), @Value);
    SET @ReturnValue = REPLICATE('0', 8 - DATALENGTH(@ReturnValue)) + @ReturnValue;

    RETURN (@ReturnValue);
END;

--- CONVERTED TARGET CODE (PostgreSQL) — use these exact routine names and signatures in target_sql / call_target ---
-- REPLICATE('0', 8 - DATALENGTH(v)) + v  ->  lpad(v, 8, '0'). WITH SCHEMABINDING dropped.
-- Values wider than 8 chars: SQL Server CONVERT(varchar(8), int) yields '*' (overflow marker),
-- DATALENGTH('*') = 1, so the result is REPLICATE('0', 7) + '*' = '0000000*' — reproduced.
CREATE OR REPLACE FUNCTION dbo.ufnleadingzeros(p_value integer)
RETURNS varchar(8) LANGUAGE sql IMMUTABLE AS $$
    SELECT CASE WHEN length(p_value::text) > 8 THEN '0000000*' ELSE lpad(p_value::text, 8, '0') END::varchar(8)
$$;

### VIEW DBO.VwCustomerShopping — write a **function and/or procedure**-shape spec
--- SOURCE (VIEW) — DBO.VwCustomerShopping ---
CREATE VIEW [dbo].[VwCustomerShopping] AS
SELECT 
    o.[OrderID],
    c.[FirstName] + ' ' + c.[LastName] AS [CustomerName],
    o.[OrderDate],
    o.[TotalAmount],
    o.[Status],
    FORMATMESSAGE(
        'Hi, %s! Your order #%s for $%s will be shipped shortly. Thank you!',
        c.[FirstName],
        CAST(o.[OrderID] AS VARCHAR),
        CAST(o.[TotalAmount] AS VARCHAR)
    ) AS [GreetingMessage]
FROM [dbo].[Shopping] o
JOIN [dbo].[Members] c ON c.[CustomerID] = o.[CustomerID];

--- CONVERTED TARGET CODE (PostgreSQL) — use these exact routine names and signatures in target_sql / call_target ---
-- '+' concat -> '||' (both yield NULL when an operand is NULL: CONCAT_NULL_YIELDS_NULL ON).
-- FORMATMESSAGE -> format(); FORMATMESSAGE renders a NULL argument as '(null)', format() as ''
-- -> coalesce(...,'(null)') keeps SQL Server's output.
CREATE OR REPLACE VIEW dbo.vwcustomershopping AS
SELECT o.orderid,
       c.firstname || ' ' || c.lastname AS customername,
       o.orderdate, o.totalamount, o.status,
       format('Hi, %s! Your order #%s for $%s will be shipped shortly. Thank you!',
              coalesce(c.firstname, '(null)'), coalesce(o.orderid::varchar, '(null)'),
              coalesce(o.totalamount::varchar, '(null)')) AS greetingmessage
FROM dbo.shopping o
JOIN dbo.members c ON c.customerid = o.customerid;

### VIEW DBO.VwOpenCoupons — write a **function and/or procedure**-shape spec
--- SOURCE (VIEW) — DBO.VwOpenCoupons ---
CREATE VIEW [dbo].[VwOpenCoupons] AS
SELECT 
    t.[TicketID], 
    c.[FirstName], 
    c.[LastName], 
    t.[IssueDescription], 
    t.[CreatedDate], 
    DATEDIFF(DAY, t.[CreatedDate], GETDATE()) AS [DaysOpen]
FROM [dbo].[Coupons] t
JOIN [dbo].[Members] c ON t.[CustomerID] = c.[CustomerID]
WHERE t.[Status] = 'Open' AND t.[OSUser] = CURRENT_USER;

--- CONVERTED TARGET CODE (PostgreSQL) — use these exact routine names and signatures in target_sql / call_target ---
-- DATEDIFF(DAY, x, GETDATE()) -> current_date - x::date.
-- BEHAVIOURAL: CURRENT_USER is the SQL Server *database user* (e.g. 'dbo'); PostgreSQL returns the
-- login role (e.g. 'postgres'). Rows filtered on osuser = CURRENT_USER differ between engines unless
-- the coupon owners are re-mapped to PostgreSQL roles — review with the application owner.
CREATE OR REPLACE VIEW dbo.vwopencoupons AS
SELECT t.ticketid, c.firstname, c.lastname, t.issuedescription, t.createddate,
       (current_date - t.createddate::date) AS daysopen
FROM dbo.coupons t
JOIN dbo.members c ON t.customerid = c.customerid
WHERE t.status = 'Open' AND t.osuser = current_user;

### VIEW DBO.VwRegionalSales — write a **function and/or procedure**-shape spec
--- SOURCE (VIEW) — DBO.VwRegionalSales ---
CREATE VIEW [dbo].[VwRegionalSales] ([RegionName], [RegionSalesSum]) AS
SELECT 
    CHOOSE([RegionID], 
           'North America', 'Europe', 'Asia', 'South America', 'Africa', 
           'Australia', 'Middle East', 'Central America', 'Eastern Europe', 
           'Western Europe') AS [RegionName],
    SUM([Quantity] * [SalePrice]) AS [RegionSalesSum]
FROM [dbo].[ProductSales]
GROUP BY CHOOSE([RegionID], 
                'North America', 'Europe', 'Asia', 'South America', 'Africa', 
                'Australia', 'Middle East', 'Central America', 'Eastern Europe', 
                'Western Europe');

--- CONVERTED TARGET CODE (PostgreSQL) — use these exact routine names and signatures in target_sql / call_target ---
-- CHOOSE(i, a, b, ...) -> (ARRAY[a, b, ...])[i]  (both NULL when i is out of range).
CREATE OR REPLACE VIEW dbo.vwregionalsales (regionname, regionsalessum) AS
SELECT (ARRAY['North America','Europe','Asia','South America','Africa','Australia','Middle East',
              'Central America','Eastern Europe','Western Europe'])[regionid::int],
       sum(quantity * saleprice)
FROM dbo.productsales
GROUP BY 1;

### VIEW DBO.VwTopMembers — write a **function and/or procedure**-shape spec
--- SOURCE (VIEW) — DBO.VwTopMembers ---
-- Create views
CREATE VIEW [dbo].[VwTopMembers] AS
SELECT * 
FROM (
    SELECT TOP 50 PERCENT 
        c.[CustomerID], 
        c.[FirstName], 
        c.[LastName], 
        SUM(o.[TotalAmount]) AS [TotalSpent]
    FROM [dbo].[Members] c
    JOIN [dbo].[Shopping] o ON c.[CustomerID] = o.[CustomerID]
    GROUP BY c.[CustomerID], c.[FirstName], c.[LastName]
    ORDER BY [TotalSpent] DESC
) sub;

--- CONVERTED TARGET CODE (PostgreSQL) — use these exact routine names and signatures in target_sql / call_target ---
-- TOP 50 PERCENT ... ORDER BY -> first ceil(50% of rows) by row_number over the same order.
-- BEHAVIOURAL: ties at the cut-off are broken arbitrarily in both engines (no WITH TIES).
CREATE OR REPLACE VIEW dbo.vwtopmembers AS
SELECT customerid, firstname, lastname, totalspent
FROM (
    SELECT c.customerid, c.firstname, c.lastname, sum(o.totalamount) AS totalspent,
           row_number() OVER (ORDER BY sum(o.totalamount) DESC) AS rn,
           count(*) OVER () AS cnt
    FROM dbo.members c
    JOIN dbo.shopping o ON c.customerid = o.customerid
    GROUP BY c.customerid, c.firstname, c.lastname
) sub
WHERE rn <= ceil(cnt * 50 / 100.0);

### PROCEDURE DBO.uspDeleteAuthor — write a **procedure**-shape spec
--- SOURCE (PROCEDURE) — DBO.uspDeleteAuthor ---
CREATE PROCEDURE [dbo].[uspDeleteAuthor]
    @BusinessEntityID [int]
WITH EXECUTE AS CALLER
AS
BEGIN
    SET NOCOUNT ON;

    BEGIN TRY
        DELETE FROM [dbo].[Author]
        WHERE [BusinessEntityID] = @BusinessEntityID;

        -- Check if the delete was successful
        IF @@ROWCOUNT = 0
        BEGIN
            RAISERROR('No author found with the provided BusinessEntityID.', 16, 1);
            RETURN;
        END
    END TRY
    BEGIN CATCH
        -- Log the error and re-throw
        EXECUTE [dbo].[uspLogError];
        THROW;
    END CATCH;
END;

--- CONVERTED TARGET CODE (PostgreSQL) — use these exact routine names and signatures in target_sql / call_target ---
-- TRY/CATCH + THROW -> EXCEPTION block + re-RAISE. @@ROWCOUNT = 0 -> NOT FOUND.
-- BEHAVIOURAL: SQL Server keeps the ErrorLog row written in CATCH before THROW; in PostgreSQL the
-- re-raised error aborts the caller's transaction, so that log row is rolled back with it
-- (no autonomous transactions). Log externally (application / pg log) if the row is required.
CREATE OR REPLACE PROCEDURE dbo.uspdeleteauthor(p_businessentityid integer)
LANGUAGE plpgsql AS $$
DECLARE
    v_msg text; v_state text; v_id integer;
BEGIN
    DELETE FROM dbo.author WHERE businessentityid = p_businessentityid;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'No author found with the provided BusinessEntityID.' USING ERRCODE = 'P0001';
    END IF;
EXCEPTION WHEN OTHERS THEN
    GET STACKED DIAGNOSTICS v_msg = MESSAGE_TEXT, v_state = RETURNED_SQLSTATE;
    CALL dbo.usplogerror(v_id, CASE WHEN v_state = 'P0001' THEN 50000 ELSE 0 END, 16, 1,
                         'uspDeleteAuthor', NULL, v_state || ': ' || v_msg);
    RAISE;
END $$;

--- SAMPLED REAL DATA (use these actual values) ---
### Members  (columns: CustomerID, FirstName, LastName, Email, Phone, RegistrationDate, TotalOrderSum)
  1 | Alice | Cooper | alice.cooper@example.com | 1112223333 | 2022-06-01 | 
  2 | Bob | Marley | bob.marley@example.com | 4445556666 | 2022-06-02 | 
  3 | Charlie | Brown | charlie.brown@example.com | 7778889999 | 2022-06-03 | 
### Shopping  (columns: OrderID, CustomerID, OrderDate, TotalAmount, Status)
  1 | 1 | 2022-01-10 00:00:00 | 100 | Delivered
  2 | 2 | 2022-02-20 00:00:00 | 75.5 | Shipped
  3 | 3 | 2022-03-25 00:00:00 | 200.75 | Processing
### Coupons  (columns: TicketID, CustomerID, OrderID, IssueDescription, CreatedDate, ResolvedDate, Status, OSUser)
  1 | 1 | 1 | Item was damaged during shipping | 2022-01-15 00:00:00 | 2022-01-20 00:00:00 | Closed | sqladmin
  2 | 2 | 2 | Order not received yet | 2022-02-25 00:00:00 |  | Open | sqladmin
  3 | 3 | 3 | Wrong item shipped | 2022-03-28 00:00:00 | 2022-04-01 00:00:00 | Closed | sqladmin
### ProductSales  (columns: SaleID, ProductID, SaleDate, Quantity, UnitPrice, TotalAmount, CustomerID, SalePrice, RegionID)
  334 | 229 | 2004-07-24 | 3 | 399.99 | 3142.85 | 385 | 416.03 | 8
  335 | 219 | 2023-08-24 | 1 | 1299.73 | 1267.45 | 336 | 1425.85 | 5
  336 | 247 | 2024-09-01 | 3 | 339.99 | 336.62 | 362 | 361.74 | 8
### Author  (columns: BusinessEntityID, NationalIDNumber, LoginID, OrganizationNode, JobTitle, BirthDate, MaritalStatus, Gender, HireDate, VacationHours, CurrentFlag, ModifiedDate)
  1 | 295847284 | adventure-works\ken0 |  | Chief Executive Officer | 1969-01-29 | S | M | 2009-01-14 | 99 | True | 2014-06-30 00:00:00
  2 | 245797967 | adventure-works\terri0 | 58 | Vice President of Engineering | 1971-08-01 | S | F | 2008-01-31 | 1 | True | 2014-06-30 00:00:00
  3 | 509647174 | adventure-works\roberto0 | 5AC0 | Engineering Manager | 1974-11-12 | M | M | 2007-11-11 | 2 | True | 2014-06-30 00:00:00
