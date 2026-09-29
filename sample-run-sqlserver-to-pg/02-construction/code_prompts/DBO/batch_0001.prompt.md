<!-- dbmig code conversion prompt
     batch: 1/4
     Convert each object and SAVE PostgreSQL code to its output file:
       - FUNCTION dbo.ufnCalculateCustomerLifetimeValue -> code/dbo/function__ufncalculatecustomerlifetimevalue.sql
       - FUNCTION dbo.ufnGetAccountingEndDate -> code/dbo/function__ufngetaccountingenddate.sql
       - FUNCTION dbo.ufnGetAccountingStartDate -> code/dbo/function__ufngetaccountingstartdate.sql
       - FUNCTION dbo.ufnGetDocumentStatusText -> code/dbo/function__ufngetdocumentstatustext.sql
       - FUNCTION dbo.ufnGetPurchaseOrderStatusText -> code/dbo/function__ufngetpurchaseorderstatustext.sql
       - FUNCTION dbo.ufnGetSalesOrderStatusText -> code/dbo/function__ufngetsalesorderstatustext.sql
       - FUNCTION dbo.ufnLeadingZeros -> code/dbo/function__ufnleadingzeros.sql
     Then set each unit's status to 'converted' in code-manifest-DBO.yaml. -->

=== CONTEXT ===
Shared code context for this run: `migrations/<project>/02-construction/_context-code.md`. Read it once per session if you have not already — it holds the customer-specific rules (highest precedence), datatype map, engine checks and playbook index this task relies on. Do not skip it.

=== TASK ===
Convert the following SQL Server stored code object to PostgreSQL (procedural SQL — e.g. PL/pgSQL). Return only valid PostgreSQL, ready to execute. Packages/modules have no direct equivalent: map each routine to its own function/procedure. Note any construct that needs human review in a SQL comment. Qualify every created object with the target schema `dbo` (derived from the source schema — do NOT use the connection's database/catalog name for qualification). Each object below is independent: convert each one and save it to its own output file (listed in the header).

--- SOURCE (FUNCTION) — dbo.ufnCalculateCustomerLifetimeValue ---
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

--- SOURCE (FUNCTION) — dbo.ufnGetAccountingEndDate ---
CREATE FUNCTION [dbo].[ufnGetAccountingEndDate]()
RETURNS [datetime] 
AS 
BEGIN
    RETURN DATEADD(millisecond, -2, CONVERT(datetime, '20040701', 112));
END;

--- SOURCE (FUNCTION) — dbo.ufnGetAccountingStartDate ---
CREATE FUNCTION [dbo].[ufnGetAccountingStartDate]()
RETURNS [datetime] 
AS 
BEGIN
    RETURN CONVERT(datetime, '20030701', 112);
END;

--- SOURCE (FUNCTION) — dbo.ufnGetDocumentStatusText ---
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

--- SOURCE (FUNCTION) — dbo.ufnGetPurchaseOrderStatusText ---
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

--- SOURCE (FUNCTION) — dbo.ufnGetSalesOrderStatusText ---
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

--- SOURCE (FUNCTION) — dbo.ufnLeadingZeros ---
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
