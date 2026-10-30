<!-- dbmig test-generation prompt  batch 3/5
     Write one test spec (YAML) per object:
       - VIEW HUMANRESOURCES.vJobCandidateEducation -> tests/HUMANRESOURCES/view__vjobcandidateeducation.test.yaml
     Then set each unit's status 'generated' in test-manifest-HUMANRESOURCES.yaml. -->

=== CONTEXT ===
Shared tests context for this run: `migrations/<project>/03-validation/_context-tests.md`. Read it once per session if you have not already — it holds the customer-specific rules (highest precedence), datatype map, engine checks and playbook index this task relies on. Do not skip it.

=== TASK — GENERATE EQUIVALENCE TESTS ===
Generate equivalence tests that prove the converted PostgreSQL (Aurora PostgreSQL compatible) view `HUMANRESOURCES.vJobCandidateEducation` behaves the same as the SQL Server source: same input → same return value (functions) or same net effect (procedures). Tests run on BOTH engines and the results are compared. Use the spec format and Rules in the context above.

### VIEW HUMANRESOURCES.vJobCandidateEducation — write a **function and/or procedure**-shape spec
--- SOURCE (VIEW) — HUMANRESOURCES.vJobCandidateEducation ---
CREATE VIEW [HumanResources].[vJobCandidateEducation] 
AS 
SELECT 
    jc.[JobCandidateID] 
    ,[Education].ref.value(N'declare default element namespace "http://schemas.microsoft.com/sqlserver/2004/07/adventure-works/Resume"; 
        (Edu.Level)[1]', 'nvarchar(max)') AS [Edu.Level]
    ,CONVERT(datetime, REPLACE([Education].ref.value(N'declare default element namespace "http://schemas.microsoft.com/sqlserver/2004/07/adventure-works/Resume"; 
        (Edu.StartDate)[1]', 'nvarchar(20)') ,'Z', ''), 101) AS [Edu.StartDate] 
    ,CONVERT(datetime, REPLACE([Education].ref.value(N'declare default element namespace "http://schemas.microsoft.com/sqlserver/2004/07/adventure-works/Resume"; 
        (Edu.EndDate)[1]', 'nvarchar(20)') ,'Z', ''), 101) AS [Edu.EndDate] 
    ,[Education].ref.value(N'declare default element namespace "http://schemas.microsoft.com/sqlserver/2004/07/adventure-works/Resume"; 
        (Edu.Degree)[1]', 'nvarchar(50)') AS [Edu.Degree]
    ,[Education].ref.value(N'declare default element namespace "http://schemas.microsoft.com/sqlserver/2004/07/adventure-works/Resume"; 
        (Edu.Major)[1]', 'nvarchar(50)') AS [Edu.Major]
    ,[Education].ref.value(N'declare default element namespace "http://schemas.microsoft.com/sqlserver/2004/07/adventure-works/Resume"; 
        (Edu.Minor)[1]', 'nvarchar(50)') AS [Edu.Minor]
    ,[Education].ref.value(N'declare default element namespace "http://schemas.microsoft.com/sqlserver/2004/07/adventure-works/Resume"; 
        (Edu.GPA)[1]', 'nvarchar(5)') AS [Edu.GPA]
    ,[Education].ref.value(N'declare default element namespace "http://schemas.microsoft.com/sqlserver/2004/07/adventure-works/Resume"; 
        (Edu.GPAScale)[1]', 'nvarchar(5)') AS [Edu.GPAScale]
    ,[Education].ref.value(N'declare default element namespace "http://schemas.microsoft.com/sqlserver/2004/07/adventure-works/Resume"; 
        (Edu.School)[1]', 'nvarchar(100)') AS [Edu.School]
    ,[Education].ref.value(N'declare default element namespace "http://schemas.microsoft.com/sqlserver/2004/07/adventure-works/Resume"; 
        (Edu.Location/Location/Loc.CountryRegion)[1]', 'nvarchar(100)') AS [Edu.Loc.CountryRegion]
    ,[Education].ref.value(N'declare default element namespace "http://schemas.microsoft.com/sqlserver/2004/07/adventure-works/Resume"; 
        (Edu.Location/Location/Loc.State)[1]', 'nvarchar(100)') AS [Edu.Loc.State]
    ,[Education].ref.value(N'declare default element namespace "http://schemas.microsoft.com/sqlserver/2004/07/adventure-works/Resume"; 
        (Edu.Location/Location/Loc.City)[1]', 'nvarchar(100)') AS [Edu.Loc.City]
FROM [HumanResources].[JobCandidate] jc 
CROSS APPLY jc.[Resume].nodes(N'declare default element namespace "http://schemas.microsoft.com/sqlserver/2004/07/adventure-works/Resume"; 
    /Resume/Education') AS [Education](ref);

--- CONVERTED TARGET CODE (PostgreSQL) — use these exact routine names and signatures in target_sql / call_target ---
CREATE OR REPLACE  VIEW adventureworks_humanresources.vjobcandidateeducation (text, error_msg) AS
SELECT 'CREATE VIEW [HumanResources].[vJobCandidateEducation] 
AS 
SELECT 
    jc.[JobCandidateID] 
    ,[Education].ref.value(N''declare default element namespace "http://schemas.microsoft.com/sqlserver/2004/07/adventure-works/Resume"; 
        (Edu.Level)[1]'', ''nvarchar(max)'') AS [Edu.Level]
    ,CONVERT(datetime, REPLACE([Education].ref.value(N''declare default element namespace "http://schemas.microsoft.com/sqlserver/2004/07/adventure-works/Resume"; 
        (Edu.StartDate)[1]'', ''nvarchar(20)'') ,''Z'', ''''), 101) AS [Edu.StartDate] 
    ,CONVERT(datetime, REPLACE([Education].ref.value(N''declare default element namespace "http://schemas.microsoft.com/sqlserver/2004/07/adventure-works/Resume"; 
        (Edu.EndDate)[1]'', ''nvarchar(20)'') ,''Z'', ''''), 101) AS [Edu.EndDate] 
    ,[Education].ref.value(N''declare default element namespace "http://schemas.microsoft.com/sqlserver/2004/07/adventure-works/Resume"; 
        (Edu.Degree)[1]'', ''nvarchar(50)'') AS [Edu.Degree]
    ,[Education].ref.value(N''declare default element namespace "http://schemas.microsoft.com/sqlserver/2004/07/adventure-works/Resume"; 
        (Edu.Major)[1]'', ''nvarchar(50)'') AS [Edu.Major]
    ,[Education].ref.value(N''declare default element namespace "http://schemas.microsoft.com/sqlserver/2004/07/adventure-works/Resume"; 
        (Edu.Minor)[1]'', ''nvarchar(50)'') AS [Edu.Minor]
    ,[Education].ref.value(N''declare default element namespace "http://schemas.microsoft.com/sqlserver/2004/07/adventure-works/Resume"; 
        (Edu.GPA)[1]'', ''nvarchar(5)'') AS [Edu.GPA]
    ,[Education].ref.value(N''declare default element namespace "http://schemas.microsoft.com/sqlserver/2004/07/adventure-works/Resume"; 
        (Edu.GPAScale)[1]'', ''nvarchar(5)'') AS [Edu.GPAScale]
    ,[Education].ref.value(N''declare default element namespace "http://schemas.microsoft.com/sqlserver/2004/07/adventure-works/Resume"; 
        (Edu.School)[1]'', ''nvarchar(100)'') AS [Edu.School]
    ,[Education].ref.value(N''declare default element namespace "http://schemas.microsoft.com/sqlserver/2004/07/adventure-works/Resume"; 
        (Edu.Location/Location/Loc.CountryRegion)[1]'', ''nvarchar(100)'') AS [Edu.Loc.CountryRegion]
    ,[Education].ref.value(N''declare default element namespace "http://schemas.microsoft.com/sqlserver/2004/07/adventure-works/Resume"; 
        (Edu.Location/Location/Loc.State)[1]'', ''nvarchar(100)'') AS [Edu.Loc.State]
    ,[Education].ref.value(N''declare default element namespace "http://schemas.microsoft.com/sqlserver/2004/07/adventure-works/Resume"; 
        (Edu.Location/Location/Loc.City)[1]'', ''nvarchar(100)'') AS [Edu.Loc.City]
FROM [HumanResources].[JobCandidate] jc 
CROSS APPLY jc.[Resume].nodes(N''declare default element namespace "http://schemas.microsoft.com/sqlserver/2004/07/adventure-works/Resume"; 
    /Resume/Education'') AS [Education](ref);'::varchar AS text,'7708 - Severity CRITICAL - DMS SC can''t convert the usage of the unsupported XML.VALUE(VARCHAR,VARCHAR) data type. Convert your source code manually.
7708 - Severity CRITICAL - DMS SC can''t convert the usage of the unsupported XML.VALUE(VARCHAR,VARCHAR) data type. Convert your source code manually.
7708 - Severity CRITICAL - DMS SC can''t convert the usage of the unsupported XML.VALUE(VARCHAR,VARCHAR) data type. Convert your source code manually.
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

--- SAMPLED REAL DATA (use these actual values) ---
### JobCandidate  (columns: JobCandidateID, BusinessEntityID, Resume, ModifiedDate)
  1 |  | <ns:Resume xmlns:ns="http://schemas.microsoft.com/sqlserver/2004/07/adventure-wo… | 2007-06-23 00:00:00
  2 |  | <ns:Resume xmlns:ns="http://schemas.microsoft.com/sqlserver/2004/07/adventure-wo… | 2007-06-23 00:00:00
  3 |  | <ns:Resume xmlns:ns="http://schemas.microsoft.com/sqlserver/2004/07/adventure-wo… | 2007-06-23 00:00:00
