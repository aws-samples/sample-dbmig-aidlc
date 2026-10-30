<!-- dbmig code conversion prompt
     batch: 3/4
     Convert each object and SAVE PostgreSQL code to its output file:
       - PROCEDURE dbo.uspDeleteAuthor -> code/dbo/procedure__uspdeleteauthor.sql
       - PROCEDURE dbo.uspDeleteOldCoupons -> code/dbo/procedure__uspdeleteoldcoupons.sql
       - PROCEDURE dbo.uspGetAuthorManagers -> code/dbo/procedure__uspgetauthormanagers.sql
       - PROCEDURE dbo.uspGetBillOfMaterials -> code/dbo/procedure__uspgetbillofmaterials.sql
       - PROCEDURE dbo.uspGetManagerAuthors -> code/dbo/procedure__uspgetmanagerauthors.sql
       - PROCEDURE dbo.uspGetProductData -> code/dbo/procedure__uspgetproductdata.sql
       - PROCEDURE dbo.uspGetTopRegion -> code/dbo/procedure__uspgettopregion.sql
       - PROCEDURE dbo.uspGetWhereUsedProductID -> code/dbo/procedure__uspgetwhereusedproductid.sql
     Then set each unit's status to 'converted' in code-manifest-DBO.yaml. -->

=== CONTEXT ===
Shared code context for this run: `migrations/<project>/02-construction/_context-code.md`. Read it once per session if you have not already — it holds the customer-specific rules (highest precedence), datatype map, engine checks and playbook index this task relies on. Do not skip it.

=== TASK ===
Convert the following SQL Server stored code object to PostgreSQL (PL/pgSQL). Return only valid PostgreSQL, ready to execute. Packages/modules have no direct equivalent: map each routine to its own function/procedure. Note any construct that needs human review in a SQL comment. Qualify every created object with the target schema `dbo` (derived from the source schema — do NOT use the connection's database/catalog name for qualification). Each object below is independent: convert each one and save it to its own output file (listed in the header).

=== CONSTRUCTS DETECTED IN THIS PROMPT'S SOURCE (apply the matching guidance; open the named playbook file when the context is not enough, and cite it in the conversion log) ===
- TOP → LIMIT (mind ORDER BY / WITH TIES) — see `skills/sqlserver-to-postgresql-playbook/references/tsql/top-fetch.md`
- @@ROWCOUNT/SCOPE_IDENTITY → GET DIAGNOSTICS / RETURNING — see `skills/sqlserver-to-postgresql-playbook/references/tsql/identity-and-sequences.md`
- TRY/CATCH/THROW → EXCEPTION blocks / RAISE — see `skills/sqlserver-to-postgresql-playbook/references/tsql/error-handling.md`
- #temp tables → CREATE TEMP TABLE
- cursor → FOR loop over query / set-based rewrite — see `skills/sqlserver-to-postgresql-playbook/references/tsql/cursors.md`
- date functions → interval arithmetic / date_part; DATEDIFF counts boundaries (current_date - d::date for DAY) — see `skills/sqlserver-to-postgresql-playbook/references/tsql/date-time-functions.md`
- ISNULL/IIF/CHOOSE → COALESCE / CASE / array index
- string functions → repeat/lpad, octet_length, length (LEN ignores trailing spaces), strpos, overlay — see `skills/sqlserver-to-postgresql-playbook/references/tsql/string-functions.md`
- TOP n PERCENT → row_number() <= ceil(count * n / 100) — see `skills/sqlserver-to-postgresql-playbook/references/tsql/top-fetch.md`
- ERROR_*() / RAISERROR → GET STACKED DIAGNOSTICS in the handler; pass fields to logging procs — see `skills/sqlserver-to-postgresql-playbook/references/tsql/error-handling.md`
- '+' string concatenation → '||' (NULL handling: CONCAT_NULL_YIELDS_NULL) — see `skills/sqlserver-to-postgresql-playbook/references/tsql/string-functions.md`
- SCHEMABINDING / SET NOCOUNT / EXECUTE AS → drop (no equivalent needed) — see `skills/sqlserver-to-postgresql-playbook/references/tsql/stored-procedures.md`
- MAXRECURSION → recursion-level guard in WITH RECURSIVE — see `skills/sqlserver-to-postgresql-playbook/references/ansi-sql/common-table-expressions.md`
- cursor OUTPUT param → set-returning function (or refcursor) — see `skills/sqlserver-to-postgresql-playbook/references/tsql/cursors.md`

--- SOURCE (PROCEDURE) — dbo.uspDeleteAuthor ---
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

--- SOURCE (PROCEDURE) — dbo.uspDeleteOldCoupons ---
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

--- SOURCE (PROCEDURE) — dbo.uspGetAuthorManagers ---
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

--- SOURCE (PROCEDURE) — dbo.uspGetBillOfMaterials ---
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

--- SOURCE (PROCEDURE) — dbo.uspGetManagerAuthors ---
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

--- SOURCE (PROCEDURE) — dbo.uspGetProductData ---
CREATE PROCEDURE [dbo].[uspGetProductData]
    @my_cursor CURSOR VARYING OUTPUT
AS
BEGIN
    -- Open a cursor for the SELECT query
    SET @my_cursor = CURSOR FOR
    SELECT
        ProductID,
        Name,
        ProductNumber,
        SafetyStockLevel
    FROM dbo.Product;
    -- Open the cursor to make it available to the caller
    OPEN @my_cursor;
END;

--- SOURCE (PROCEDURE) — dbo.uspGetTopRegion ---
-- Create procedures
CREATE PROCEDURE [dbo].[uspGetTopRegion]
    @Percent INT
AS
BEGIN
    WITH [HalfYearSales] AS (
        SELECT 
            psr.[RegionID],
            psr.[RegionName],
            COUNT(ps.[SaleID]) AS [NumberOfSales],
            SUM(ps.[TotalAmount]) AS [TotalSalesAmount],
            COUNT(DISTINCT ps.[CustomerID]) AS [NumberOfMembers]
        FROM 
            [dbo].[ProductSaleRegions] psr
        LEFT JOIN 
            [dbo].[ProductSales] ps ON psr.[RegionID] = ps.[RegionID]
        WHERE 
            ps.[SaleDate] >= DATEADD(MONTH, -6, GETDATE())
        GROUP BY 
            psr.[RegionID], psr.[RegionName]
    )
    SELECT * FROM (
        SELECT TOP 10 PERCENT * FROM [HalfYearSales] WHERE @Percent = 10 ORDER BY [NumberOfSales] DESC
        UNION ALL 
        SELECT TOP 20 PERCENT * FROM [HalfYearSales] WHERE @Percent = 20 ORDER BY [NumberOfSales] DESC
        UNION ALL 
        SELECT TOP 30 PERCENT * FROM [HalfYearSales] WHERE @Percent = 30 ORDER BY [NumberOfSales] DESC
        UNION ALL 
        SELECT TOP 40 PERCENT * FROM [HalfYearSales] WHERE @Percent = 40 ORDER BY [NumberOfSales] DESC
        UNION ALL 
        SELECT TOP 50 PERCENT * FROM [HalfYearSales] WHERE @Percent = 50 ORDER BY [NumberOfSales] DESC
    ) q
    ORDER BY [NumberOfSales] DESC, [TotalSalesAmount] DESC;
END;

--- SOURCE (PROCEDURE) — dbo.uspGetWhereUsedProductID ---
CREATE PROCEDURE [dbo].[uspGetWhereUsedProductID]
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
            ON b.[ProductAssemblyID] = p.[ProductID] 
        WHERE b.[ComponentID] = @StartProductID 
            AND @CheckDate >= b.[StartDate] 
            AND @CheckDate <= ISNULL(b.[EndDate], @CheckDate)
        UNION ALL
        SELECT b.[ProductAssemblyID], b.[ComponentID], p.[Name], b.[PerAssemblyQty], p.[StandardCost], p.[ListPrice], b.[BOMLevel], [RecursionLevel] + 1 
        FROM [BOM_cte] cte
            INNER JOIN [dbo].[BillOfMaterials] b 
            ON cte.[ProductAssemblyID] = b.[ComponentID]
            INNER JOIN [dbo].[Product] p 
            ON b.[ProductAssemblyID] = p.[ProductID] 
        WHERE @CheckDate >= b.[StartDate] 
            AND @CheckDate <= ISNULL(b.[EndDate], @CheckDate)
        )
    SELECT b.[ProductAssemblyID], b.[ComponentID], b.[ComponentDesc], SUM(b.[PerAssemblyQty]) AS [TotalQuantity] , b.[StandardCost], b.[ListPrice], b.[BOMLevel], b.[RecursionLevel]
    FROM [BOM_cte] b
    GROUP BY b.[ComponentID], b.[ComponentDesc], b.[ProductAssemblyID], b.[BOMLevel], b.[RecursionLevel], b.[StandardCost], b.[ListPrice]
    ORDER BY b.[BOMLevel], b.[ProductAssemblyID], b.[ComponentID]
    OPTION (MAXRECURSION 25) 
END;
