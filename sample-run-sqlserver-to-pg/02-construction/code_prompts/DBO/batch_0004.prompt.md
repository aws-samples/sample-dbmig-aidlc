<!-- dbmig code conversion prompt
     batch: 4/4
     Convert each object and SAVE PostgreSQL code to its output file:
       - PROCEDURE dbo.uspLogError -> code/dbo/procedure__usplogerror.sql
       - PROCEDURE dbo.uspPrintError -> code/dbo/procedure__uspprinterror.sql
       - PROCEDURE dbo.uspProcessRefunds -> code/dbo/procedure__uspprocessrefunds.sql
       - PROCEDURE dbo.uspShoppingLevelAmount -> code/dbo/procedure__uspshoppinglevelamount.sql
       - PROCEDURE dbo.uspUpdateAuthorLogin -> code/dbo/procedure__uspupdateauthorlogin.sql
       - PROCEDURE dbo.uspUpdateAuthorPersonalInfo -> code/dbo/procedure__uspupdateauthorpersonalinfo.sql
     Then set each unit's status to 'converted' in code-manifest-DBO.yaml. -->

=== CONTEXT ===
Shared code context for this run: `migrations/<project>/02-construction/_context-code.md`. Read it once per session if you have not already — it holds the customer-specific rules (highest precedence), datatype map, engine checks and playbook index this task relies on. Do not skip it.

=== TASK ===
Convert the following SQL Server stored code object to PostgreSQL (procedural SQL — e.g. PL/pgSQL). Return only valid PostgreSQL, ready to execute. Packages/modules have no direct equivalent: map each routine to its own function/procedure. Note any construct that needs human review in a SQL comment. Qualify every created object with the target schema `dbo` (derived from the source schema — do NOT use the connection's database/catalog name for qualification). Each object below is independent: convert each one and save it to its own output file (listed in the header).

=== CONSTRUCTS DETECTED IN THIS OBJECT (apply the matching guidance in the context) ===
- @@ROWCOUNT/SCOPE_IDENTITY → GET DIAGNOSTICS / RETURNING
- TRY/CATCH/THROW → EXCEPTION blocks / RAISE
- #temp tables → CREATE TEMP TABLE

--- SOURCE (PROCEDURE) — dbo.uspLogError ---
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

--- SOURCE (PROCEDURE) — dbo.uspPrintError ---
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

--- SOURCE (PROCEDURE) — dbo.uspProcessRefunds ---
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

--- SOURCE (PROCEDURE) — dbo.uspShoppingLevelAmount ---
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

--- SOURCE (PROCEDURE) — dbo.uspUpdateAuthorLogin ---
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

--- SOURCE (PROCEDURE) — dbo.uspUpdateAuthorPersonalInfo ---
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
