<!-- dbmig test-generation prompt  batch 4/5
     Write one test spec (YAML) per object:
       - PROCEDURE DBO.uspGetProductData -> tests/DBO/procedure__uspgetproductdata.test.yaml
       - PROCEDURE DBO.uspGetTopRegion -> tests/DBO/procedure__uspgettopregion.test.yaml
       - PROCEDURE DBO.uspGetWhereUsedProductID -> tests/DBO/procedure__uspgetwhereusedproductid.test.yaml
       - PROCEDURE DBO.uspLogError -> tests/DBO/procedure__usplogerror.test.yaml
       - PROCEDURE DBO.uspPrintError -> tests/DBO/procedure__uspprinterror.test.yaml
     Then set each unit's status 'generated' in test-manifest-DBO.yaml. -->
<!-- LOW_COVERAGE uspLogError: every table it reads is EMPTY in the source (ErrorLog) — cases only exercise the empty/default path; state this in `notes:`. -->

=== CONTEXT ===
Shared tests context for this run: `migrations/<project>/03-validation/_context-tests.md`. Read it once per session if you have not already — it holds the customer-specific rules (highest precedence), datatype map, engine checks and playbook index this task relies on. Do not skip it.

=== TASK — GENERATE EQUIVALENCE TESTS ===
Generate equivalence tests that prove each of the 5 converted PostgreSQL (Aurora PostgreSQL compatible) objects below (one spec file per object, as listed in the header) behaves the same as the SQL Server source: same input → same return value (functions) or same net effect (procedures). Tests run on BOTH engines and the results are compared. Use the spec format and Rules in the context above.

### PROCEDURE DBO.uspGetProductData — write a **procedure**-shape spec
--- SOURCE (PROCEDURE) — DBO.uspGetProductData ---
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

--- CONVERTED TARGET CODE (PostgreSQL) — use these exact routine names and signatures in target_sql / call_target ---
-- CURSOR VARYING OUTPUT -> set-returning FUNCTION (the app consumes it as a normal query:
-- SELECT * FROM dbo.uspgetproductdata()). A refcursor would have to be fetched inside the same
-- transaction; the result-set form is the recommended conversion (app call-site change).
CREATE OR REPLACE FUNCTION dbo.uspgetproductdata()
RETURNS TABLE (productid integer, name varchar, productnumber varchar, safetystocklevel smallint)
LANGUAGE sql STABLE AS $$
    SELECT productid, name::varchar, productnumber::varchar, safetystocklevel FROM dbo.product
$$;

### PROCEDURE DBO.uspGetTopRegion — write a **procedure**-shape spec
--- SOURCE (PROCEDURE) — DBO.uspGetTopRegion ---
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

--- CONVERTED TARGET CODE (PostgreSQL) — use these exact routine names and signatures in target_sql / call_target ---
-- Result-set procedure -> set-returning FUNCTION. The five "TOP n PERCENT ... WHERE @Percent = n"
-- branches select ceil(n% of rows) by NumberOfSales DESC; any other @Percent returns no rows.
-- The LEFT JOIN is effectively inner (WHERE on ps.saledate) — preserved as written.
-- COUNT() returns bigint in PostgreSQL (int in SQL Server). Ties at the cut-off are arbitrary.
CREATE OR REPLACE FUNCTION dbo.uspgettopregion(p_percent integer)
RETURNS TABLE (regionid integer, regionname varchar, numberofsales bigint, totalsalesamount numeric, numberofmembers bigint)
LANGUAGE sql STABLE AS $$
    WITH halfyearsales AS (
        SELECT psr.regionid, psr.regionname::varchar AS regionname, count(ps.saleid) AS numberofsales,
               sum(ps.totalamount) AS totalsalesamount, count(DISTINCT ps.customerid) AS numberofmembers
        FROM dbo.productsaleregions psr
        LEFT JOIN dbo.productsales ps ON psr.regionid = ps.regionid
        WHERE ps.saledate >= (localtimestamp - interval '6 months')
        GROUP BY psr.regionid, psr.regionname
    ), ranked AS (
        SELECT h.*, row_number() OVER (ORDER BY h.numberofsales DESC) AS rn, count(*) OVER () AS cnt
        FROM halfyearsales h
    )
    SELECT regionid, regionname, numberofsales, totalsalesamount, numberofmembers
    FROM ranked
    WHERE p_percent IN (10, 20, 30, 40, 50) AND rn <= ceil(cnt * p_percent / 100.0)
    ORDER BY numberofsales DESC, totalsalesamount DESC
$$;

### PROCEDURE DBO.uspGetWhereUsedProductID — write a **procedure**-shape spec
--- SOURCE (PROCEDURE) — DBO.uspGetWhereUsedProductID ---
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

--- CONVERTED TARGET CODE (PostgreSQL) — use these exact routine names and signatures in target_sql / call_target ---
-- Result-set procedure -> set-returning FUNCTION (call: SELECT * FROM dbo.uspgetwhereusedproductid(id, date)).
-- ISNULL -> coalesce. MAXRECURSION 25 -> recursionlevel < 25 guard (see uspgetauthormanagers).
-- RETURNS TABLE types match the converted columns / aggregates exactly (SUM(numeric) = numeric).
CREATE OR REPLACE FUNCTION dbo.uspgetwhereusedproductid(p_startproductid integer, p_checkdate timestamp(3))
RETURNS TABLE (productassemblyid integer, componentid integer, componentdesc varchar, totalquantity numeric,
               standardcost numeric, listprice numeric, bomlevel smallint, recursionlevel integer)
LANGUAGE sql STABLE AS $$
    WITH RECURSIVE bom_cte (productassemblyid, componentid, componentdesc, perassemblyqty, standardcost, listprice, bomlevel, recursionlevel) AS (
        SELECT b.productassemblyid, b.componentid, p.name, b.perassemblyqty, p.standardcost, p.listprice, b.bomlevel, 0
        FROM dbo.billofmaterials b JOIN dbo.product p ON b.productassemblyid = p.productid
        WHERE b.componentid = p_startproductid AND p_checkdate >= b.startdate AND p_checkdate <= coalesce(b.enddate, p_checkdate)
        UNION ALL
        SELECT b.productassemblyid, b.componentid, p.name, b.perassemblyqty, p.standardcost, p.listprice, b.bomlevel, cte.recursionlevel + 1
        FROM bom_cte cte
        JOIN dbo.billofmaterials b ON cte.productassemblyid = b.componentid
        JOIN dbo.product p ON b.productassemblyid = p.productid
        WHERE p_checkdate >= b.startdate AND p_checkdate <= coalesce(b.enddate, p_checkdate)
          AND cte.recursionlevel < 25
    )
    SELECT b.productassemblyid, b.componentid, b.componentdesc::varchar, sum(b.perassemblyqty),
           b.standardcost, b.listprice, b.bomlevel, b.recursionlevel
    FROM bom_cte b
    GROUP BY b.componentid, b.componentdesc, b.productassemblyid, b.bomlevel, b.recursionlevel, b.standardcost, b.listprice
    ORDER BY b.bomlevel, b.productassemblyid, b.componentid
$$;

### PROCEDURE DBO.uspLogError — write a **procedure**-shape spec
--- SOURCE (PROCEDURE) — DBO.uspLogError ---
CREATE   PROCEDURE [dbo].[uspLogError] 
    @ErrorLogID [int] = 0 OUTPUT 
AS
BEGIN
    SET NOCOUNT ON;
    SET @ErrorLogID = 0;

    BEGIN TRY
        IF ERROR_NUMBER() IS NULL
            RETURN;

        INSERT [dbo].[ErrorLog] 
            (
            [UserName], 
            [ErrorNumber], 
            [ErrorSeverity], 
            [ErrorState], 
            [ErrorProcedure], 
            [ErrorLine], 
            [ErrorMessage]
            ) 
        VALUES 
            (
            SUSER_SNAME(), 
            ERROR_NUMBER(),
            ERROR_SEVERITY(),
            ERROR_STATE(),
            ERROR_PROCEDURE(),
            ERROR_LINE(),
            ERROR_MESSAGE()
            );

        SET @ErrorLogID = SCOPE_IDENTITY();
    END TRY
    BEGIN CATCH
        PRINT 'An error occurred in stored procedure uspLogError: ';
        EXECUTE [dbo].[uspPrintError];
        RETURN -1;
    END CATCH
END;

--- CONVERTED TARGET CODE (PostgreSQL) — use these exact routine names and signatures in target_sql / call_target ---
-- Redesign: SQL Server reads ERROR_NUMBER()/… ambiently inside CATCH; PostgreSQL callers pass
-- them (GET STACKED DIAGNOSTICS in the caller's handler). SCOPE_IDENTITY() -> RETURNING.
-- SUSER_SNAME() -> session_user. Error number: SQL Server numbers (e.g. 50000 = RAISERROR)
-- have no PostgreSQL equivalent; callers pass 50000 for user errors and 0 otherwise, and put
-- the SQLSTATE in the message.
CREATE OR REPLACE PROCEDURE dbo.usplogerror(
    INOUT p_errorlogid integer DEFAULT 0,
    p_errornumber integer DEFAULT NULL, p_severity integer DEFAULT NULL, p_state integer DEFAULT NULL,
    p_procedure varchar DEFAULT NULL, p_line integer DEFAULT NULL, p_message varchar DEFAULT NULL)
LANGUAGE plpgsql AS $$
BEGIN
    p_errorlogid := 0;
    IF p_errornumber IS NULL THEN
        RETURN;
    END IF;
    INSERT INTO dbo.errorlog (username, errornumber, errorseverity, errorstate, errorprocedure, errorline, errormessage)
    VALUES (session_user, p_errornumber, p_severity, p_state, p_procedure, p_line, p_message)
    RETURNING errorlogid INTO p_errorlogid;
EXCEPTION WHEN OTHERS THEN
    RAISE NOTICE 'An error occurred in stored procedure uspLogError: ';
    CALL dbo.uspprinterror(0, NULL, NULL, 'usplogerror', NULL, SQLERRM);
    p_errorlogid := -1;
END $$;

### PROCEDURE DBO.uspPrintError — write a **procedure**-shape spec
--- SOURCE (PROCEDURE) — DBO.uspPrintError ---
CREATE PROCEDURE [dbo].[uspPrintError] 
AS
BEGIN
    SET NOCOUNT ON;

    -- Print error information. 
    PRINT 'Error ' + CONVERT(varchar(50), ERROR_NUMBER()) +
          ', Severity ' + CONVERT(varchar(5), ERROR_SEVERITY()) +
          ', State ' + CONVERT(varchar(5), ERROR_STATE()) + 
          ', Procedure ' + ISNULL(ERROR_PROCEDURE(), '-') + 
          ', Line ' + CONVERT(varchar(5), ERROR_LINE());
    PRINT ERROR_MESSAGE();
END;

--- CONVERTED TARGET CODE (PostgreSQL) — use these exact routine names and signatures in target_sql / call_target ---
-- ERROR_*() ambient state is not readable from a nested routine in PostgreSQL: the caller
-- passes the fields (checklist item 6). PRINT -> RAISE NOTICE.
CREATE OR REPLACE PROCEDURE dbo.uspprinterror(p_errornumber integer, p_severity integer, p_state integer,
                                              p_procedure varchar, p_line integer, p_message varchar)
LANGUAGE plpgsql AS $$
BEGIN
    RAISE NOTICE 'Error %, Severity %, State %, Procedure %, Line %',
        p_errornumber, p_severity, p_state, coalesce(p_procedure, '-'), p_line;
    RAISE NOTICE '%', p_message;
END $$;

--- SAMPLED REAL DATA (use these actual values) ---
### Product  (columns: ProductID, Name, ProductNumber, MakeFlag, FinishedGoodsFlag, Color, SafetyStockLevel, ReorderPoint, StandardCost, ListPrice, Size, SizeUnitMeasureCode, WeightUnitMeasureCode, Weight, DaysToManufacture, ProductLine, Class, Style, ProductSubcategoryID, ProductModelID, SellStartDate, SellEndDate, DiscontinuedDate, rowguid, ModifiedDate)
  1 | Adjustable Race | AR-5381 | False | False |  | 1000 | 750 | 0 | 0 |  |  |  |  | 0 |  |  |  |  |  | 2008-04-30 00:00:00 |  |  | 694215b7-08f7-4c0d-acb1-d734ba44c0c8 | 2025-08-25 02:04:20.260000
  2 | Bearing Ball | BA-8327 | False | False |  | 1000 | 750 | 0 | 0 |  |  |  |  | 0 |  |  |  |  |  | 2008-04-30 00:00:00 |  |  | 58ae3c20-4f3a-4749-a7d4-d568806cc537 | 2025-08-25 02:04:20.260000
  3 | BB Ball Bearing | BE-2349 | True | False |  | 800 | 600 | 0 | 0 |  |  |  |  | 1 |  |  |  |  |  | 2008-04-30 00:00:00 |  |  | 9c21aed2-5bfa-4f18-bcb8-f11638dc2e4e | 2025-08-25 02:04:20.260000
### ProductSaleRegions  (columns: RegionID, RegionName)
  1 | North America
  2 | Europe
  3 | Asia
### ProductSales  (columns: SaleID, ProductID, SaleDate, Quantity, UnitPrice, TotalAmount, CustomerID, SalePrice, RegionID)
  334 | 229 | 2004-07-24 | 3 | 399.99 | 3142.85 | 385 | 416.03 | 8
  335 | 219 | 2023-08-24 | 1 | 1299.73 | 1267.45 | 336 | 1425.85 | 5
  336 | 247 | 2024-09-01 | 3 | 339.99 | 336.62 | 362 | 361.74 | 8
### BillOfMaterials  (columns: BillOfMaterialsID, ProductAssemblyID, ComponentID, StartDate, EndDate, UnitMeasureCode, BOMLevel, PerAssemblyQty, ModifiedDate)
  1 | 893 | 749 | 2010-05-26 00:00:00 |  | EA  | 0 | 1 | 2010-05-12 00:00:00
  2 | 271 | 750 | 2010-03-04 00:00:00 | 2010-05-03 00:00:00 | EA  | 0 | 1 | 2010-05-03 00:00:00
  3 | 34 | 750 | 2010-05-04 00:00:00 |  | EA  | 0 | 1 | 2010-04-20 00:00:00
