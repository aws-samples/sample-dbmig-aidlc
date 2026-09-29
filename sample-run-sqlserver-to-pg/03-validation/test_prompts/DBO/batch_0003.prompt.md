<!-- dbmig test-generation prompt  batch 3/5
     Write one test spec (YAML) per object:
       - PROCEDURE DBO.uspDeleteOldCoupons -> tests/DBO/procedure__uspdeleteoldcoupons.test.yaml
       - PROCEDURE DBO.uspGetAuthorManagers -> tests/DBO/procedure__uspgetauthormanagers.test.yaml
       - PROCEDURE DBO.uspGetBillOfMaterials -> tests/DBO/procedure__uspgetbillofmaterials.test.yaml
       - PROCEDURE DBO.uspGetManagerAuthors -> tests/DBO/procedure__uspgetmanagerauthors.test.yaml
     Then set each unit's status 'generated' in test-manifest-DBO.yaml. -->

=== CONTEXT ===
Shared tests context for this run: `migrations/<project>/03-validation/_context-tests.md`. Read it once per session if you have not already — it holds the customer-specific rules (highest precedence), datatype map, engine checks and playbook index this task relies on. Do not skip it.

=== TASK — GENERATE EQUIVALENCE TESTS ===
Generate equivalence tests that prove each of the 4 converted PostgreSQL (Aurora PostgreSQL compatible) objects below (one spec file per object, as listed in the header) behaves the same as the SQL Server source: same input → same return value (functions) or same net effect (procedures). Tests run on BOTH engines and the results are compared. Use the spec format and Rules in the context above.

### PROCEDURE DBO.uspDeleteOldCoupons — write a **procedure**-shape spec
--- SOURCE (PROCEDURE) — DBO.uspDeleteOldCoupons ---
CREATE   PROCEDURE [dbo].[uspDeleteOldCoupons]
    @DaysOld INT
AS
BEGIN
    DECLARE @DeletedCount INT = 0;
    
    SELECT [TicketID], [CreatedDate]
    INTO #CouponsToDelete
    FROM [dbo].[Coupons]
    WHERE TRIM([Status]) = 'Closed' AND [ResolvedDate] <= DATEADD(DAY, -@DaysOld, GETDATE());

    DECLARE @CouponsCount INT;
    SELECT @CouponsCount = COUNT(*) FROM #CouponsToDelete;

    IF @CouponsCount > 0
    BEGIN
        DELETE t
        FROM [dbo].[Coupons] t
        INNER JOIN #CouponsToDelete d ON t.[TicketID] = d.[TicketID];
        
        SET @DeletedCount = @@ROWCOUNT;
        PRINT 'Deleted ' + CAST(@DeletedCount AS NVARCHAR(10)) + ' coupons.';
    END
    ELSE
    BEGIN
        PRINT 'No coupons found matching the criteria.';
    END
END;

--- CONVERTED TARGET CODE (PostgreSQL) — use these exact routine names and signatures in target_sql / call_target ---
-- #temp table -> set-based DELETE (the temp table only staged the key set).
-- DATEADD(DAY, -n, GETDATE()) -> localtimestamp - n days. PRINT -> RAISE NOTICE.
CREATE OR REPLACE PROCEDURE dbo.uspdeleteoldcoupons(p_daysold integer)
LANGUAGE plpgsql AS $$
DECLARE
    v_deleted integer := 0;
BEGIN
    DELETE FROM dbo.coupons
    WHERE trim(status) = 'Closed' AND resolveddate <= localtimestamp - p_daysold * interval '1 day';
    GET DIAGNOSTICS v_deleted = ROW_COUNT;
    IF v_deleted > 0 THEN
        RAISE NOTICE 'Deleted % coupons.', v_deleted;
    ELSE
        RAISE NOTICE 'No coupons found matching the criteria.';
    END IF;
END $$;

### PROCEDURE DBO.uspGetAuthorManagers — write a **procedure**-shape spec
--- SOURCE (PROCEDURE) — DBO.uspGetAuthorManagers ---
CREATE PROCEDURE [dbo].[uspGetAuthorManagers]
    @BusinessEntityID [int]
AS
BEGIN
    SET NOCOUNT ON;
    WITH [EMP_cte]([BusinessEntityID], [OrganizationNode], [FirstName], [LastName], [JobTitle], [RecursionLevel]) 
    AS (
        SELECT e.[BusinessEntityID], e.[OrganizationNode], p.[FirstName], p.[LastName], e.[JobTitle], 0 
        FROM [dbo].[Author] e 
            INNER JOIN [dbo].[Person] as p
            ON p.[BusinessEntityID] = e.[BusinessEntityID]
        WHERE e.[BusinessEntityID] = @BusinessEntityID
        UNION ALL
        SELECT e.[BusinessEntityID], e.[OrganizationNode], p.[FirstName], p.[LastName], e.[JobTitle], [RecursionLevel] + 1 
        FROM [dbo].[Author] e 
            INNER JOIN [EMP_cte]
            ON LEFT(e.[OrganizationNode], LEN(e.[OrganizationNode]) - 1) = [EMP_cte].[OrganizationNode]
            INNER JOIN [dbo].[Person] p 
            ON p.[BusinessEntityID] = e.[BusinessEntityID]
    )
    SELECT [EMP_cte].[RecursionLevel], [EMP_cte].[BusinessEntityID], [EMP_cte].[FirstName], [EMP_cte].[LastName], 
        [EMP_cte].[OrganizationNode] AS [OrganizationNode], p.[FirstName] AS 'ManagerFirstName', p.[LastName] AS 'ManagerLastName'  
    FROM [EMP_cte] 
        INNER JOIN [dbo].[Author] e 
        ON LEFT([EMP_cte].[OrganizationNode], LEN([EMP_cte].[OrganizationNode]) - 1) = e.[OrganizationNode]
        INNER JOIN [dbo].[Person] p 
        ON p.[BusinessEntityID] = e.[BusinessEntityID]
    ORDER BY [RecursionLevel], [EMP_cte].[OrganizationNode]
    OPTION (MAXRECURSION 25) 
END;

--- CONVERTED TARGET CODE (PostgreSQL) — use these exact routine names and signatures in target_sql / call_target ---
-- Result-set procedure -> set-returning FUNCTION (call: SELECT * FROM dbo.uspgetauthormanagers(id)).
-- LEFT(x, LEN(x)-1) -> left(x, length(x) - 1). OPTION (MAXRECURSION 25) -> recursionlevel < 25
-- guard (BEHAVIOURAL: SQL Server raises an error past 25 levels; the guard stops silently).
CREATE OR REPLACE FUNCTION dbo.uspgetauthormanagers(p_businessentityid integer)
RETURNS TABLE (recursionlevel integer, businessentityid integer, firstname varchar, lastname varchar, organizationnode varchar, managerfirstname varchar, managerlastname varchar)
LANGUAGE sql STABLE AS $$
    WITH RECURSIVE emp_cte (businessentityid, organizationnode, firstname, lastname, jobtitle, recursionlevel) AS (
        SELECT e.businessentityid, e.organizationnode, p.firstname, p.lastname, e.jobtitle, 0
        FROM dbo.author e JOIN dbo.person p ON p.businessentityid = e.businessentityid
        WHERE e.businessentityid = p_businessentityid
        UNION ALL
        SELECT e.businessentityid, e.organizationnode, p.firstname, p.lastname, e.jobtitle, emp_cte.recursionlevel + 1
        FROM dbo.author e
        JOIN emp_cte ON left(e.organizationnode, length(e.organizationnode) - 1) = emp_cte.organizationnode
        JOIN dbo.person p ON p.businessentityid = e.businessentityid
        WHERE emp_cte.recursionlevel < 25
    )
    SELECT emp_cte.recursionlevel, emp_cte.businessentityid, emp_cte.firstname, emp_cte.lastname, emp_cte.organizationnode, p.firstname, p.lastname
    FROM emp_cte
    JOIN dbo.author e ON left(emp_cte.organizationnode, length(emp_cte.organizationnode) - 1) = e.organizationnode
    JOIN dbo.person p ON p.businessentityid = e.businessentityid
    ORDER BY emp_cte.recursionlevel, emp_cte.organizationnode
$$;

### PROCEDURE DBO.uspGetBillOfMaterials — write a **procedure**-shape spec
--- SOURCE (PROCEDURE) — DBO.uspGetBillOfMaterials ---
CREATE PROCEDURE [dbo].[uspGetBillOfMaterials]
    @StartProductID [int],
    @CheckDate [datetime]
AS
BEGIN
    SET NOCOUNT ON;
    WITH [BOM_cte]([ProductAssemblyID], [ComponentID], [ComponentDesc], [PerAssemblyQty], [StandardCost], [ListPrice], [BOMLevel], [RecursionLevel]) 
    AS (
        SELECT b.[ProductAssemblyID], b.[ComponentID], p.[Name], b.[PerAssemblyQty], p.[StandardCost], p.[ListPrice], b.[BOMLevel], 0 
        FROM [dbo].[BillOfMaterials] b
            INNER JOIN [dbo].[Product] p 
            ON b.[ComponentID] = p.[ProductID] 
        WHERE b.[ProductAssemblyID] = @StartProductID 
            AND @CheckDate >= b.[StartDate] 
            AND @CheckDate <= ISNULL(b.[EndDate], @CheckDate)
        UNION ALL
        SELECT b.[ProductAssemblyID], b.[ComponentID], p.[Name], b.[PerAssemblyQty], p.[StandardCost], p.[ListPrice], b.[BOMLevel], [RecursionLevel] + 1 
        FROM [BOM_cte] cte
            INNER JOIN [dbo].[BillOfMaterials] b 
            ON b.[ProductAssemblyID] = cte.[ComponentID]
            INNER JOIN [dbo].[Product] p 
            ON b.[ComponentID] = p.[ProductID] 
        WHERE @CheckDate >= b.[StartDate] 
            AND @CheckDate <= ISNULL(b.[EndDate], @CheckDate)
        )
    SELECT b.[ProductAssemblyID], b.[ComponentID], b.[ComponentDesc], SUM(b.[PerAssemblyQty]) AS [TotalQuantity] , b.[StandardCost], b.[ListPrice], b.[BOMLevel], b.[RecursionLevel]
    FROM [BOM_cte] b
    GROUP BY b.[ComponentID], b.[ComponentDesc], b.[ProductAssemblyID], b.[BOMLevel], b.[RecursionLevel], b.[StandardCost], b.[ListPrice]
    ORDER BY b.[BOMLevel], b.[ProductAssemblyID], b.[ComponentID]
    OPTION (MAXRECURSION 25) 
END;

--- CONVERTED TARGET CODE (PostgreSQL) — use these exact routine names and signatures in target_sql / call_target ---
-- Result-set procedure -> set-returning FUNCTION (call: SELECT * FROM dbo.uspgetbillofmaterials(id, date)).
-- ISNULL -> coalesce. MAXRECURSION 25 -> recursionlevel < 25 guard (see uspgetauthormanagers).
-- RETURNS TABLE types match the converted columns / aggregates exactly (SUM(numeric) = numeric).
CREATE OR REPLACE FUNCTION dbo.uspgetbillofmaterials(p_startproductid integer, p_checkdate timestamp(3))
RETURNS TABLE (productassemblyid integer, componentid integer, componentdesc varchar, totalquantity numeric,
               standardcost numeric, listprice numeric, bomlevel smallint, recursionlevel integer)
LANGUAGE sql STABLE AS $$
    WITH RECURSIVE bom_cte (productassemblyid, componentid, componentdesc, perassemblyqty, standardcost, listprice, bomlevel, recursionlevel) AS (
        SELECT b.productassemblyid, b.componentid, p.name, b.perassemblyqty, p.standardcost, p.listprice, b.bomlevel, 0
        FROM dbo.billofmaterials b JOIN dbo.product p ON b.componentid = p.productid
        WHERE b.productassemblyid = p_startproductid AND p_checkdate >= b.startdate AND p_checkdate <= coalesce(b.enddate, p_checkdate)
        UNION ALL
        SELECT b.productassemblyid, b.componentid, p.name, b.perassemblyqty, p.standardcost, p.listprice, b.bomlevel, cte.recursionlevel + 1
        FROM bom_cte cte
        JOIN dbo.billofmaterials b ON b.productassemblyid = cte.componentid
        JOIN dbo.product p ON b.componentid = p.productid
        WHERE p_checkdate >= b.startdate AND p_checkdate <= coalesce(b.enddate, p_checkdate)
          AND cte.recursionlevel < 25
    )
    SELECT b.productassemblyid, b.componentid, b.componentdesc::varchar, sum(b.perassemblyqty),
           b.standardcost, b.listprice, b.bomlevel, b.recursionlevel
    FROM bom_cte b
    GROUP BY b.componentid, b.componentdesc, b.productassemblyid, b.bomlevel, b.recursionlevel, b.standardcost, b.listprice
    ORDER BY b.bomlevel, b.productassemblyid, b.componentid
$$;

### PROCEDURE DBO.uspGetManagerAuthors — write a **procedure**-shape spec
--- SOURCE (PROCEDURE) — DBO.uspGetManagerAuthors ---
CREATE PROCEDURE [dbo].[uspGetManagerAuthors]
    @BusinessEntityID [int]
AS
BEGIN
    SET NOCOUNT ON;

    WITH [EMP_cte]([BusinessEntityID], [OrganizationNode], [FirstName], [LastName], [RecursionLevel]) 
    AS (
        SELECT e.[BusinessEntityID], e.[OrganizationNode], p.[FirstName], p.[LastName], 0 
        FROM [dbo].[Author] e 
            INNER JOIN [dbo].[Person] p 
            ON p.[BusinessEntityID] = e.[BusinessEntityID]
        WHERE e.[BusinessEntityID] = @BusinessEntityID
        UNION ALL
        SELECT e.[BusinessEntityID], e.[OrganizationNode], p.[FirstName], p.[LastName], [RecursionLevel] + 1
        FROM [dbo].[Author] e 
            INNER JOIN [EMP_cte]
            ON e.[OrganizationNode] = LEFT([EMP_cte].[OrganizationNode], LEN([EMP_cte].[OrganizationNode]) - 1)
            INNER JOIN [dbo].[Person] p 
            ON p.[BusinessEntityID] = e.[BusinessEntityID]
        )
    SELECT [EMP_cte].[RecursionLevel], [EMP_cte].[OrganizationNode] as [OrganizationNode], 
           p.[FirstName] AS 'ManagerFirstName', p.[LastName] AS 'ManagerLastName',
           [EMP_cte].[BusinessEntityID], [EMP_cte].[FirstName], [EMP_cte].[LastName] 
    FROM [EMP_cte] 
        INNER JOIN [dbo].[Author] e 
        ON e.[OrganizationNode] = LEFT([EMP_cte].[OrganizationNode], LEN([EMP_cte].[OrganizationNode]) - 1)
        INNER JOIN [dbo].[Person] p 
        ON p.[BusinessEntityID] = e.[BusinessEntityID]
    ORDER BY [RecursionLevel], [EMP_cte].[OrganizationNode]
    OPTION (MAXRECURSION 25) 
END;

--- CONVERTED TARGET CODE (PostgreSQL) — use these exact routine names and signatures in target_sql / call_target ---
-- Result-set procedure -> set-returning FUNCTION (call: SELECT * FROM dbo.uspgetmanagerauthors(id)).
-- LEFT(x, LEN(x)-1) -> left(x, length(x) - 1). OPTION (MAXRECURSION 25) -> recursionlevel < 25
-- guard (BEHAVIOURAL: SQL Server raises an error past 25 levels; the guard stops silently).
CREATE OR REPLACE FUNCTION dbo.uspgetmanagerauthors(p_businessentityid integer)
RETURNS TABLE (recursionlevel integer, organizationnode varchar, managerfirstname varchar, managerlastname varchar, businessentityid integer, firstname varchar, lastname varchar)
LANGUAGE sql STABLE AS $$
    WITH RECURSIVE emp_cte (businessentityid, organizationnode, firstname, lastname, recursionlevel) AS (
        SELECT e.businessentityid, e.organizationnode, p.firstname, p.lastname, 0
        FROM dbo.author e JOIN dbo.person p ON p.businessentityid = e.businessentityid
        WHERE e.businessentityid = p_businessentityid
        UNION ALL
        SELECT e.businessentityid, e.organizationnode, p.firstname, p.lastname, emp_cte.recursionlevel + 1
        FROM dbo.author e
        JOIN emp_cte ON e.organizationnode = left(emp_cte.organizationnode, length(emp_cte.organizationnode) - 1)
        JOIN dbo.person p ON p.businessentityid = e.businessentityid
        WHERE emp_cte.recursionlevel < 25
    )
    SELECT emp_cte.recursionlevel, emp_cte.organizationnode, p.firstname, p.lastname, emp_cte.businessentityid, emp_cte.firstname, emp_cte.lastname
    FROM emp_cte
    JOIN dbo.author e ON e.organizationnode = left(emp_cte.organizationnode, length(emp_cte.organizationnode) - 1)
    JOIN dbo.person p ON p.businessentityid = e.businessentityid
    ORDER BY emp_cte.recursionlevel, emp_cte.organizationnode
$$;

--- SAMPLED REAL DATA (use these actual values) ---
### Coupons  (columns: TicketID, CustomerID, OrderID, IssueDescription, CreatedDate, ResolvedDate, Status, OSUser)
  1 | 1 | 1 | Item was damaged during shipping | 2022-01-15 00:00:00 | 2022-01-20 00:00:00 | Closed | sqladmin
  2 | 2 | 2 | Order not received yet | 2022-02-25 00:00:00 |  | Open | sqladmin
  3 | 3 | 3 | Wrong item shipped | 2022-03-28 00:00:00 | 2022-04-01 00:00:00 | Closed | sqladmin
### Author  (columns: BusinessEntityID, NationalIDNumber, LoginID, OrganizationNode, JobTitle, BirthDate, MaritalStatus, Gender, HireDate, VacationHours, CurrentFlag, ModifiedDate)
  1 | 295847284 | adventure-works\ken0 |  | Chief Executive Officer | 1969-01-29 | S | M | 2009-01-14 | 99 | True | 2014-06-30 00:00:00
  2 | 245797967 | adventure-works\terri0 | 58 | Vice President of Engineering | 1971-08-01 | S | F | 2008-01-31 | 1 | True | 2014-06-30 00:00:00
  3 | 509647174 | adventure-works\roberto0 | 5AC0 | Engineering Manager | 1974-11-12 | M | M | 2007-11-11 | 2 | True | 2014-06-30 00:00:00
### Person  (columns: BusinessEntityID, PersonType, NameStyle, Title, FirstName, MiddleName, LastName, Suffix, EmailPromotion, AdditionalContactInfo, Demographics, rowguid, ModifiedDate)
  1 | EM | False |  | Ken | J | SÃ¡nchez |  | 0 |  | <IndividualSurvey xmlns="http://schemas.microsoft.com/sqlserver/2004/07/adventur… | 92c4279f-1207-48a3-8448-4636514eb7e2 | 2009-01-07 00:00:00
  2 | EM | False |  | Terri | Lee | Duffy |  | 1 |  | <IndividualSurvey xmlns="http://schemas.microsoft.com/sqlserver/2004/07/adventur… | d8763459-8aa8-47cc-aff7-c9079af79033 | 2008-01-24 00:00:00
  3 | EM | False |  | Roberto |  | Tamburello |  | 0 |  | <IndividualSurvey xmlns="http://schemas.microsoft.com/sqlserver/2004/07/adventur… | e1a2555e-0828-434b-a33b-6f38136a37de | 2007-11-04 00:00:00
### BillOfMaterials  (columns: BillOfMaterialsID, ProductAssemblyID, ComponentID, StartDate, EndDate, UnitMeasureCode, BOMLevel, PerAssemblyQty, ModifiedDate)
  1 | 893 | 749 | 2010-05-26 00:00:00 |  | EA  | 0 | 1 | 2010-05-12 00:00:00
  2 | 271 | 750 | 2010-03-04 00:00:00 | 2010-05-03 00:00:00 | EA  | 0 | 1 | 2010-05-03 00:00:00
  3 | 34 | 750 | 2010-05-04 00:00:00 |  | EA  | 0 | 1 | 2010-04-20 00:00:00
### Product  (columns: ProductID, Name, ProductNumber, MakeFlag, FinishedGoodsFlag, Color, SafetyStockLevel, ReorderPoint, StandardCost, ListPrice, Size, SizeUnitMeasureCode, WeightUnitMeasureCode, Weight, DaysToManufacture, ProductLine, Class, Style, ProductSubcategoryID, ProductModelID, SellStartDate, SellEndDate, DiscontinuedDate, rowguid, ModifiedDate)
  1 | Adjustable Race | AR-5381 | False | False |  | 1000 | 750 | 0 | 0 |  |  |  |  | 0 |  |  |  |  |  | 2008-04-30 00:00:00 |  |  | 694215b7-08f7-4c0d-acb1-d734ba44c0c8 | 2025-08-25 02:04:20.260000
  2 | Bearing Ball | BA-8327 | False | False |  | 1000 | 750 | 0 | 0 |  |  |  |  | 0 |  |  |  |  |  | 2008-04-30 00:00:00 |  |  | 58ae3c20-4f3a-4749-a7d4-d568806cc537 | 2025-08-25 02:04:20.260000
  3 | BB Ball Bearing | BE-2349 | True | False |  | 800 | 600 | 0 | 0 |  |  |  |  | 1 |  |  |  |  |  | 2008-04-30 00:00:00 |  |  | 9c21aed2-5bfa-4f18-bcb8-f11638dc2e4e | 2025-08-25 02:04:20.260000
