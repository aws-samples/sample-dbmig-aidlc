<!-- dbmig test-generation prompt  batch 4/5
     Write one test spec (YAML) per object:
       - VIEW HUMANRESOURCES.vJobCandidateEmployment -> tests/HUMANRESOURCES/view__vjobcandidateemployment.test.yaml
       - PROCEDURE HUMANRESOURCES.uspUpdateEmployeeHireInfo -> tests/HUMANRESOURCES/procedure__uspupdateemployeehireinfo.test.yaml
       - PROCEDURE HUMANRESOURCES.uspUpdateEmployeeLogin -> tests/HUMANRESOURCES/procedure__uspupdateemployeelogin.test.yaml
     Then set each unit's status 'generated' in test-manifest-HUMANRESOURCES.yaml. -->
<!-- CAUTION uspUpdateEmployeeHireInfo: manages its own transaction (COMMIT/ROLLBACK/BEGIN TRAN) — NOT safely net-effect testable via the rollback harness. Write a NON-DESTRUCTIVE case (e.g. a non-existent key) or leave 'cases: []' and note it. -->

=== CONTEXT ===
Shared tests context for this run: `migrations/<project>/03-validation/_context-tests.md`. Read it once per session if you have not already — it holds the customer-specific rules (highest precedence), datatype map, engine checks and playbook index this task relies on. Do not skip it.

=== TASK — GENERATE EQUIVALENCE TESTS ===
Generate equivalence tests that prove each of the 3 converted PostgreSQL (Aurora PostgreSQL compatible) objects below (one spec file per object, as listed in the header) behaves the same as the SQL Server source: same input → same return value (functions) or same net effect (procedures). Tests run on BOTH engines and the results are compared. Use the spec format and Rules in the context above.

### VIEW HUMANRESOURCES.vJobCandidateEmployment — write a **function and/or procedure**-shape spec
--- SOURCE (VIEW) — HUMANRESOURCES.vJobCandidateEmployment ---
CREATE VIEW [HumanResources].[vJobCandidateEmployment] 
AS 
SELECT 
    jc.[JobCandidateID] 
    ,CONVERT(datetime, REPLACE([Employment].ref.value(N'declare default element namespace "http://schemas.microsoft.com/sqlserver/2004/07/adventure-works/Resume"; 
        (Emp.StartDate)[1]', 'nvarchar(20)') ,'Z', ''), 101) AS [Emp.StartDate] 
    ,CONVERT(datetime, REPLACE([Employment].ref.value(N'declare default element namespace "http://schemas.microsoft.com/sqlserver/2004/07/adventure-works/Resume"; 
        (Emp.EndDate)[1]', 'nvarchar(20)') ,'Z', ''), 101) AS [Emp.EndDate] 
    ,[Employment].ref.value(N'declare default element namespace "http://schemas.microsoft.com/sqlserver/2004/07/adventure-works/Resume"; 
        (Emp.OrgName)[1]', 'nvarchar(100)') AS [Emp.OrgName]
    ,[Employment].ref.value(N'declare default element namespace "http://schemas.microsoft.com/sqlserver/2004/07/adventure-works/Resume"; 
        (Emp.JobTitle)[1]', 'nvarchar(100)') AS [Emp.JobTitle]
    ,[Employment].ref.value(N'declare default element namespace "http://schemas.microsoft.com/sqlserver/2004/07/adventure-works/Resume"; 
        (Emp.Responsibility)[1]', 'nvarchar(max)') AS [Emp.Responsibility]
    ,[Employment].ref.value(N'declare default element namespace "http://schemas.microsoft.com/sqlserver/2004/07/adventure-works/Resume"; 
        (Emp.FunctionCategory)[1]', 'nvarchar(max)') AS [Emp.FunctionCategory]
    ,[Employment].ref.value(N'declare default element namespace "http://schemas.microsoft.com/sqlserver/2004/07/adventure-works/Resume"; 
        (Emp.IndustryCategory)[1]', 'nvarchar(max)') AS [Emp.IndustryCategory]
    ,[Employment].ref.value(N'declare default element namespace "http://schemas.microsoft.com/sqlserver/2004/07/adventure-works/Resume"; 
        (Emp.Location/Location/Loc.CountryRegion)[1]', 'nvarchar(max)') AS [Emp.Loc.CountryRegion]
    ,[Employment].ref.value(N'declare default element namespace "http://schemas.microsoft.com/sqlserver/2004/07/adventure-works/Resume"; 
        (Emp.Location/Location/Loc.State)[1]', 'nvarchar(max)') AS [Emp.Loc.State]
    ,[Employment].ref.value(N'declare default element namespace "http://schemas.microsoft.com/sqlserver/2004/07/adventure-works/Resume"; 
        (Emp.Location/Location/Loc.City)[1]', 'nvarchar(max)') AS [Emp.Loc.City]
FROM [HumanResources].[JobCandidate] jc 
CROSS APPLY jc.[Resume].nodes(N'declare default element namespace "http://schemas.microsoft.com/sqlserver/2004/07/adventure-works/Resume"; 
    /Resume/Employment') AS Employment(ref);

--- CONVERTED TARGET CODE (PostgreSQL) — use these exact routine names and signatures in target_sql / call_target ---
CREATE OR REPLACE  VIEW adventureworks_humanresources.vjobcandidateemployment (text, error_msg) AS
SELECT 'CREATE VIEW [HumanResources].[vJobCandidateEmployment] 
AS 
SELECT 
    jc.[JobCandidateID] 
    ,CONVERT(datetime, REPLACE([Employment].ref.value(N''declare default element namespace "http://schemas.microsoft.com/sqlserver/2004/07/adventure-works/Resume"; 
        (Emp.StartDate)[1]'', ''nvarchar(20)'') ,''Z'', ''''), 101) AS [Emp.StartDate] 
    ,CONVERT(datetime, REPLACE([Employment].ref.value(N''declare default element namespace "http://schemas.microsoft.com/sqlserver/2004/07/adventure-works/Resume"; 
        (Emp.EndDate)[1]'', ''nvarchar(20)'') ,''Z'', ''''), 101) AS [Emp.EndDate] 
    ,[Employment].ref.value(N''declare default element namespace "http://schemas.microsoft.com/sqlserver/2004/07/adventure-works/Resume"; 
        (Emp.OrgName)[1]'', ''nvarchar(100)'') AS [Emp.OrgName]
    ,[Employment].ref.value(N''declare default element namespace "http://schemas.microsoft.com/sqlserver/2004/07/adventure-works/Resume"; 
        (Emp.JobTitle)[1]'', ''nvarchar(100)'') AS [Emp.JobTitle]
    ,[Employment].ref.value(N''declare default element namespace "http://schemas.microsoft.com/sqlserver/2004/07/adventure-works/Resume"; 
        (Emp.Responsibility)[1]'', ''nvarchar(max)'') AS [Emp.Responsibility]
    ,[Employment].ref.value(N''declare default element namespace "http://schemas.microsoft.com/sqlserver/2004/07/adventure-works/Resume"; 
        (Emp.FunctionCategory)[1]'', ''nvarchar(max)'') AS [Emp.FunctionCategory]
    ,[Employment].ref.value(N''declare default element namespace "http://schemas.microsoft.com/sqlserver/2004/07/adventure-works/Resume"; 
        (Emp.IndustryCategory)[1]'', ''nvarchar(max)'') AS [Emp.IndustryCategory]
    ,[Employment].ref.value(N''declare default element namespace "http://schemas.microsoft.com/sqlserver/2004/07/adventure-works/Resume"; 
        (Emp.Location/Location/Loc.CountryRegion)[1]'', ''nvarchar(max)'') AS [Emp.Loc.CountryRegion]
    ,[Employment].ref.value(N''declare default element namespace "http://schemas.microsoft.com/sqlserver/2004/07/adventure-works/Resume"; 
        (Emp.Location/Location/Loc.State)[1]'', ''nvarchar(max)'') AS [Emp.Loc.State]
    ,[Employment].ref.value(N''declare default element namespace "http://schemas.microsoft.com/sqlserver/2004/07/adventure-works/Resume"; 
        (Emp.Location/Location/Loc.City)[1]'', ''nvarchar(max)'') AS [Emp.Loc.City]
FROM [HumanResources].[JobCandidate] jc 
CROSS APPLY jc.[Resume].nodes(N''declare default element namespace "http://schemas.microsoft.com/sqlserver/2004/07/adventure-works/Resume"; 
    /Resume/Employment'') AS Employment(ref);'::varchar AS text,'7708 - Severity CRITICAL - DMS SC can''t convert the usage of the unsupported XML.VALUE(VARCHAR,VARCHAR) data type. Convert your source code manually.
7708 - Severity CRITICAL - DMS SC can''t convert the usage of the unsupported XML.VALUE(VARCHAR,VARCHAR) data type. Convert your source code manually.
7708 - Severity CRITICAL - DMS SC can''t convert the usage of the unsupported XML.VALUE(VARCHAR,VARCHAR) data type. Convert your source code manually.
7708 - Severity CRITICAL - DMS SC can''t convert the usage of the unsupported XML.VALUE(VARCHAR,VARCHAR) data type. Convert your source code manually.
7708 - Severity CRITICAL - DMS SC can''t convert the usage of the unsupported XML.VALUE(VARCHAR,VARCHAR) data type. Convert your source code manually.
7708 - Severity CRITICAL - DMS SC can''t convert the usage of the unsupported XML.VALUE(VARCHAR,VARCHAR) data type. Convert your source code manually.
7708 - Severity CRITICAL - DMS SC can''t convert the usage of the unsupported XML.VALUE(VARCHAR,VARCHAR) data type. Convert your source code manually.
7708 - Severity CRITICAL - DMS SC can''t convert the usage of the unsupported XML.VALUE(VARCHAR,VARCHAR) data type. Convert your source code manually.
7708 - Severity CRITICAL - DMS SC can''t convert the usage of the unsupported XML.VALUE(VARCHAR,VARCHAR) data type. Convert your source code manually.
7708 - Severity CRITICAL - DMS SC can''t convert the usage of the unsupported XML.VALUE(VARCHAR,VARCHAR) data type. Convert your source code manually.
7708 - Severity CRITICAL - DMS SC can''t convert the usage of the unsupported XML.NODES(VARCHAR) data type. Convert your source code manually.
'::varchar AS error_msg;

### PROCEDURE HUMANRESOURCES.uspUpdateEmployeeHireInfo — write a **procedure**-shape spec
--- SOURCE (PROCEDURE) — HUMANRESOURCES.uspUpdateEmployeeHireInfo ---
CREATE PROCEDURE [HumanResources].[uspUpdateEmployeeHireInfo]
    @BusinessEntityID [int], 
    @JobTitle [nvarchar](50), 
    @HireDate [datetime], 
    @RateChangeDate [datetime], 
    @Rate [money], 
    @PayFrequency [tinyint], 
    @CurrentFlag [dbo].[Flag] 
WITH EXECUTE AS CALLER
AS
BEGIN
    SET NOCOUNT ON;

    BEGIN TRY
        BEGIN TRANSACTION;

        UPDATE [HumanResources].[Employee] 
        SET [JobTitle] = @JobTitle 
            ,[HireDate] = @HireDate 
            ,[CurrentFlag] = @CurrentFlag 
        WHERE [BusinessEntityID] = @BusinessEntityID;

        INSERT INTO [HumanResources].[EmployeePayHistory] 
            ([BusinessEntityID]
            ,[RateChangeDate]
            ,[Rate]
            ,[PayFrequency]) 
        VALUES (@BusinessEntityID, @RateChangeDate, @Rate, @PayFrequency);

        COMMIT TRANSACTION;
    END TRY
    BEGIN CATCH
        -- Rollback any active or uncommittable transactions before
        -- inserting information in the ErrorLog
        IF @@TRANCOUNT > 0
        BEGIN
            ROLLBACK TRANSACTION;
        END

        EXECUTE [dbo].[uspLogError];
    END CATCH;
END;

--- CONVERTED TARGET CODE (PostgreSQL) — use these exact routine names and signatures in target_sql / call_target ---
-- MANUAL reconversion of HumanResources.uspUpdateEmployeeHireInfo (7644, 7807, 7615, 7811).
-- EXECUTE AS CALLER dropped (PG procedures run as the caller by default). BEGIN TRAN/COMMIT removed:
-- a procedure called inside an EXCEPTION block cannot COMMIT (7615); the block itself gives the
-- source's all-or-nothing behaviour, and the handler logs then re-raises like the source's THROW.
CREATE OR REPLACE PROCEDURE adventureworks_humanresources.uspupdateemployeehireinfo(IN par_businessentityid integer, IN par_jobtitle character varying, IN par_hiredate timestamp without time zone, IN par_ratechangedate timestamp without time zone, IN par_rate numeric, IN par_payfrequency smallint, IN par_currentflag adventureworks_dbo.flag)
 LANGUAGE plpgsql
AS $procedure$
DECLARE
    usplogerror$par_ErrorLogID INTEGER;
    usplogerror$ReturnCode INTEGER;
BEGIN
    UPDATE adventureworks_humanresources.employee
       SET jobtitle = par_jobtitle, hiredate = par_hiredate, currentflag = par_currentflag
     WHERE businessentityid = par_businessentityid;
    INSERT INTO adventureworks_humanresources.employeepayhistory (businessentityid, ratechangedate, rate, payfrequency)
    VALUES (par_businessentityid, par_ratechangedate, par_rate, par_payfrequency);
EXCEPTION
    WHEN OTHERS THEN
        CALL adventureworks_dbo.usplogerror(par_ErrorLogID => usplogerror$par_ErrorLogID, return_code => usplogerror$ReturnCode);
END;
$procedure$;

### PROCEDURE HUMANRESOURCES.uspUpdateEmployeeLogin — write a **procedure**-shape spec
--- SOURCE (PROCEDURE) — HUMANRESOURCES.uspUpdateEmployeeLogin ---
CREATE PROCEDURE [HumanResources].[uspUpdateEmployeeLogin]
    @BusinessEntityID [int], 
    @OrganizationNode [hierarchyid],
    @LoginID [nvarchar](256),
    @JobTitle [nvarchar](50),
    @HireDate [datetime],
    @CurrentFlag [dbo].[Flag]
WITH EXECUTE AS CALLER
AS
BEGIN
    SET NOCOUNT ON;

    BEGIN TRY
        UPDATE [HumanResources].[Employee] 
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
-- MANUAL reconversion of HumanResources.uspUpdateEmployeeLogin (7644, 7657, 7706).
-- DMS SC commented the UPDATE out (hierarchyid parameter, 7657) and left an EMPTY body, so the
-- converted procedure silently did nothing. The UPDATE is restored with organizationnode as
-- varchar (the hierarchyid string form '/1/2/', matching how the column was converted).
CREATE OR REPLACE PROCEDURE adventureworks_humanresources.uspupdateemployeelogin(IN par_businessentityid integer, IN par_organizationnode character varying, IN par_loginid character varying, IN par_jobtitle character varying, IN par_hiredate timestamp without time zone, IN par_currentflag adventureworks_dbo.flag)
 LANGUAGE plpgsql
AS $procedure$
DECLARE
    usplogerror$par_ErrorLogID INTEGER;
    usplogerror$ReturnCode INTEGER;
BEGIN
    UPDATE adventureworks_humanresources.employee
       SET organizationnode = par_organizationnode, loginid = par_loginid, jobtitle = par_jobtitle,
           hiredate = par_hiredate, currentflag = par_currentflag
     WHERE businessentityid = par_businessentityid;
EXCEPTION
    WHEN OTHERS THEN
        CALL adventureworks_dbo.usplogerror(par_ErrorLogID => usplogerror$par_ErrorLogID, return_code => usplogerror$ReturnCode);
END;
$procedure$;

--- SAMPLED REAL DATA (use these actual values) ---
### JobCandidate  (columns: JobCandidateID, BusinessEntityID, Resume, ModifiedDate)
  1 |  | <ns:Resume xmlns:ns="http://schemas.microsoft.com/sqlserver/2004/07/adventure-wo… | 2007-06-23 00:00:00
  2 |  | <ns:Resume xmlns:ns="http://schemas.microsoft.com/sqlserver/2004/07/adventure-wo… | 2007-06-23 00:00:00
  3 |  | <ns:Resume xmlns:ns="http://schemas.microsoft.com/sqlserver/2004/07/adventure-wo… | 2007-06-23 00:00:00
### Employee  (columns: BusinessEntityID, NationalIDNumber, LoginID, OrganizationNode, OrganizationLevel, JobTitle, BirthDate, MaritalStatus, Gender, HireDate, SalariedFlag, VacationHours, SickLeaveHours, CurrentFlag, rowguid, ModifiedDate)
  1 | 295847284 | adventure-works\ken0 |  |  | Chief Executive Officer | 1969-01-29 | S | M | 2009-01-14 | True | 99 | 69 | True | f01251e5-96a3-448d-981e-0f99d789110d | 2014-06-30 00:00:00
  2 | 245797967 | adventure-works\terri0 | <binary 1 bytes> | 1 | Vice President of Engineering | 1971-08-01 | S | F | 2008-01-31 | True | 1 | 20 | True | 45e8f437-670d-4409-93cb-f9424a40d6ee | 2014-06-30 00:00:00
  3 | 509647174 | adventure-works\roberto0 | <binary 2 bytes> | 2 | Engineering Manager | 1974-11-12 | M | M | 2007-11-11 | True | 2 | 21 | True | 9bbbfb2c-efbb-4217-9ab7-f97689328841 | 2014-06-30 00:00:00
### EmployeePayHistory  (columns: BusinessEntityID, RateChangeDate, Rate, PayFrequency, ModifiedDate)
  1 | 2009-01-14 00:00:00 | 125.5 | 2 | 2014-06-30 00:00:00
  2 | 2008-01-31 00:00:00 | 63.4615 | 2 | 2014-06-30 00:00:00
  3 | 2007-11-11 00:00:00 | 43.2692 | 2 | 2014-06-30 00:00:00
