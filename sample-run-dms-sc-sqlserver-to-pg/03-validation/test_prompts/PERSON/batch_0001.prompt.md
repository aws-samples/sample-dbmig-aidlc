<!-- dbmig test-generation prompt  batch 1/1
     Write one test spec (YAML) per object:
       - VIEW PERSON.vAdditionalContactInfo -> tests/PERSON/view__vadditionalcontactinfo.test.yaml
       - VIEW PERSON.vStateProvinceCountryRegion -> tests/PERSON/view__vstateprovincecountryregion.test.yaml
     Then set each unit's status 'generated' in test-manifest-PERSON.yaml. -->

=== CONTEXT ===
Shared tests context for this run: `migrations/<project>/03-validation/_context-tests.md`. Read it once per session if you have not already — it holds the customer-specific rules (highest precedence), datatype map, engine checks and playbook index this task relies on. Do not skip it.

=== TASK — GENERATE EQUIVALENCE TESTS ===
Generate equivalence tests that prove each of the 2 converted PostgreSQL (Aurora PostgreSQL compatible) objects below (one spec file per object, as listed in the header) behaves the same as the SQL Server source: same input → same return value (functions) or same net effect (procedures). Tests run on BOTH engines and the results are compared. Use the spec format and Rules in the context above.

### VIEW PERSON.vAdditionalContactInfo — write a **function and/or procedure**-shape spec
--- SOURCE (VIEW) — PERSON.vAdditionalContactInfo ---
CREATE VIEW [Person].[vAdditionalContactInfo] 
AS 
SELECT 
    [BusinessEntityID] 
    ,[FirstName]
    ,[MiddleName]
    ,[LastName]
    ,[ContactInfo].ref.value(N'declare namespace ci="http://schemas.microsoft.com/sqlserver/2004/07/adventure-works/ContactInfo"; 
        declare namespace act="http://schemas.microsoft.com/sqlserver/2004/07/adventure-works/ContactTypes"; 
        (act:telephoneNumber)[1]/act:number', 'nvarchar(50)') AS [TelephoneNumber] 
    ,LTRIM(RTRIM([ContactInfo].ref.value(N'declare namespace ci="http://schemas.microsoft.com/sqlserver/2004/07/adventure-works/ContactInfo"; 
        declare namespace act="http://schemas.microsoft.com/sqlserver/2004/07/adventure-works/ContactTypes"; 
        (act:telephoneNumber/act:SpecialInstructions/text())[1]', 'nvarchar(max)'))) AS [TelephoneSpecialInstructions] 
    ,[ContactInfo].ref.value(N'declare namespace ci="http://schemas.microsoft.com/sqlserver/2004/07/adventure-works/ContactInfo"; 
        declare namespace act="http://schemas.microsoft.com/sqlserver/2004/07/adventure-works/ContactTypes";
        (act:homePostalAddress/act:Street)[1]', 'nvarchar(50)') AS [Street] 
    ,[ContactInfo].ref.value(N'declare namespace ci="http://schemas.microsoft.com/sqlserver/2004/07/adventure-works/ContactInfo"; 
        declare namespace act="http://schemas.microsoft.com/sqlserver/2004/07/adventure-works/ContactTypes"; 
        (act:homePostalAddress/act:City)[1]', 'nvarchar(50)') AS [City] 
    ,[ContactInfo].ref.value(N'declare namespace ci="http://schemas.microsoft.com/sqlserver/2004/07/adventure-works/ContactInfo"; 
        declare namespace act="http://schemas.microsoft.com/sqlserver/2004/07/adventure-works/ContactTypes"; 
        (act:homePostalAddress/act:StateProvince)[1]', 'nvarchar(50)') AS [StateProvince] 
    ,[ContactInfo].ref.value(N'declare namespace ci="http://schemas.microsoft.com/sqlserver/2004/07/adventure-works/ContactInfo"; 
        declare namespace act="http://schemas.microsoft.com/sqlserver/2004/07/adventure-works/ContactTypes"; 
        (act:homePostalAddress/act:PostalCode)[1]', 'nvarchar(50)') AS [PostalCode] 
    ,[ContactInfo].ref.value(N'declare namespace ci="http://schemas.microsoft.com/sqlserver/2004/07/adventure-works/ContactInfo"; 
        declare namespace act="http://schemas.microsoft.com/sqlserver/2004/07/adventure-works/ContactTypes"; 
        (act:homePostalAddress/act:CountryRegion)[1]', 'nvarchar(50)') AS [CountryRegion] 
    ,[ContactInfo].ref.value(N'declare namespace ci="http://schemas.microsoft.com/sqlserver/2004/07/adventure-works/ContactInfo"; 
        declare namespace act="http://schemas.microsoft.com/sqlserver/2004/07/adventure-works/ContactTypes"; 
        (act:homePostalAddress/act:SpecialInstructions/text())[1]', 'nvarchar(max)') AS [HomeAddressSpecialInstructions] 
    ,[ContactInfo].ref.value(N'declare namespace ci="http://schemas.microsoft.com/sqlserver/2004/07/adventure-works/ContactInfo"; 
        declare namespace act="http://schemas.microsoft.com/sqlserver/2004/07/adventure-works/ContactTypes"; 
        (act:eMail/act:eMailAddress)[1]', 'nvarchar(128)') AS [EMailAddress] 
    ,LTRIM(RTRIM([ContactInfo].ref.value(N'declare namespace ci="http://schemas.microsoft.com/sqlserver/2004/07/adventure-works/ContactInfo"; 
        declare namespace act="http://schemas.microsoft.com/sqlserver/2004/07/adventure-works/ContactTypes"; 
        (act:eMail/act:SpecialInstructions/text())[1]', 'nvarchar(max)'))) AS [EMailSpecialInstructions] 
    ,[ContactInfo].ref.value(N'declare namespace ci="http://schemas.microsoft.com/sqlserver/2004/07/adventure-works/ContactInfo"; 
        declare namespace act="http://schemas.microsoft.com/sqlserver/2004/07/adventure-works/ContactTypes"; 
        (act:eMail/act:SpecialInstructions/act:telephoneNumber/act:number)[1]', 'nvarchar(50)') AS [EMailTelephoneNumber] 
    ,[rowguid] 
    ,[ModifiedDate]
FROM [Person].[Person]
OUTER APPLY [AdditionalContactInfo].nodes(
    'declare namespace ci="http://schemas.microsoft.com/sqlserver/2004/07/adventure-works/ContactInfo"; 
    /ci:AdditionalContactInfo') AS ContactInfo(ref) 
WHERE [AdditionalContactInfo] IS NOT NULL;

--- CONVERTED TARGET CODE (PostgreSQL) — use these exact routine names and signatures in target_sql / call_target ---
CREATE OR REPLACE  VIEW adventureworks_person.vadditionalcontactinfo (text, error_msg) AS
SELECT 'CREATE VIEW [Person].[vAdditionalContactInfo] 
AS 
SELECT 
    [BusinessEntityID] 
    ,[FirstName]
    ,[MiddleName]
    ,[LastName]
    ,[ContactInfo].ref.value(N''declare namespace ci="http://schemas.microsoft.com/sqlserver/2004/07/adventure-works/ContactInfo"; 
        declare namespace act="http://schemas.microsoft.com/sqlserver/2004/07/adventure-works/ContactTypes"; 
        (act:telephoneNumber)[1]/act:number'', ''nvarchar(50)'') AS [TelephoneNumber] 
    ,LTRIM(RTRIM([ContactInfo].ref.value(N''declare namespace ci="http://schemas.microsoft.com/sqlserver/2004/07/adventure-works/ContactInfo"; 
        declare namespace act="http://schemas.microsoft.com/sqlserver/2004/07/adventure-works/ContactTypes"; 
        (act:telephoneNumber/act:SpecialInstructions/text())[1]'', ''nvarchar(max)''))) AS [TelephoneSpecialInstructions] 
    ,[ContactInfo].ref.value(N''declare namespace ci="http://schemas.microsoft.com/sqlserver/2004/07/adventure-works/ContactInfo"; 
        declare namespace act="http://schemas.microsoft.com/sqlserver/2004/07/adventure-works/ContactTypes";
        (act:homePostalAddress/act:Street)[1]'', ''nvarchar(50)'') AS [Street] 
    ,[ContactInfo].ref.value(N''declare namespace ci="http://schemas.microsoft.com/sqlserver/2004/07/adventure-works/ContactInfo"; 
        declare namespace act="http://schemas.microsoft.com/sqlserver/2004/07/adventure-works/ContactTypes"; 
        (act:homePostalAddress/act:City)[1]'', ''nvarchar(50)'') AS [City] 
    ,[ContactInfo].ref.value(N''declare namespace ci="http://schemas.microsoft.com/sqlserver/2004/07/adventure-works/ContactInfo"; 
        declare namespace act="http://schemas.microsoft.com/sqlserver/2004/07/adventure-works/ContactTypes"; 
        (act:homePostalAddress/act:StateProvince)[1]'', ''nvarchar(50)'') AS [StateProvince] 
    ,[ContactInfo].ref.value(N''declare namespace ci="http://schemas.microsoft.com/sqlserver/2004/07/adventure-works/ContactInfo"; 
        declare namespace act="http://schemas.microsoft.com/sqlserver/2004/07/adventure-works/ContactTypes"; 
        (act:homePostalAddress/act:PostalCode)[1]'', ''nvarchar(50)'') AS [PostalCode] 
    ,[ContactInfo].ref.value(N''declare namespace ci="http://schemas.microsoft.com/sqlserver/2004/07/adventure-works/ContactInfo"; 
        declare namespace act="http://schemas.microsoft.com/sqlserver/2004/07/adventure-works/ContactTypes"; 
        (act:homePostalAddress/act:CountryRegion)[1]'', ''nvarchar(50)'') AS [CountryRegion] 
    ,[ContactInfo].ref.value(N''declare namespace ci="http://schemas.microsoft.com/sqlserver/2004/07/adventure-works/ContactInfo"; 
        declare namespace act="http://schemas.microsoft.com/sqlserver/2004/07/adventure-works/ContactTypes"; 
        (act:homePostalAddress/act:SpecialInstructions/text())[1]'', ''nvarchar(max)'') AS [HomeAddressSpecialInstructions] 
    ,[ContactInfo].ref.value(N''declare namespace ci="http://schemas.microsoft.com/sqlserver/2004/07/adventure-works/ContactInfo"; 
        declare namespace act="http://schemas.microsoft.com/sqlserver/2004/07/adventure-works/ContactTypes"; 
        (act:eMail/act:eMailAddress)[1]'', ''nvarchar(128)'') AS [EMailAddress] 
    ,LTRIM(RTRIM([ContactInfo].ref.value(N''declare namespace ci="http://schemas.microsoft.com/sqlserver/2004/07/adventure-works/ContactInfo"; 
        declare namespace act="http://schemas.microsoft.com/sqlserver/2004/07/adventure-works/ContactTypes"; 
        (act:eMail/act:SpecialInstructions/text())[1]'', ''nvarchar(max)''))) AS [EMailSpecialInstructions] 
    ,[ContactInfo].ref.value(N''declare namespace ci="http://schemas.microsoft.com/sqlserver/2004/07/adventure-works/ContactInfo"; 
        declare namespace act="http://schemas.microsoft.com/sqlserver/2004/07/adventure-works/ContactTypes"; 
        (act:eMail/act:SpecialInstructions/act:telephoneNumber/act:number)[1]'', ''nvarchar(50)'') AS [EMailTelephoneNumber] 
    ,[rowguid] 
    ,[ModifiedDate]
FROM [Person].[Person]
OUTER APPLY [AdditionalContactInfo].nodes(
    ''declare namespace ci="http://schemas.microsoft.com/sqlserver/2004/07/adventure-works/ContactInfo"; 
    /ci:AdditionalContactInfo'') AS ContactInfo(ref) 
WHERE [AdditionalContactInfo] IS NOT NULL;'::varchar AS text,'7708 - Severity CRITICAL - DMS SC can''t convert the usage of the unsupported XML.VALUE(VARCHAR,VARCHAR) data type. Convert your source code manually.
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

### VIEW PERSON.vStateProvinceCountryRegion — write a **function and/or procedure**-shape spec
--- SOURCE (VIEW) — PERSON.vStateProvinceCountryRegion ---
CREATE VIEW [Person].[vStateProvinceCountryRegion] 
WITH SCHEMABINDING 
AS 
SELECT 
    sp.[StateProvinceID] 
    ,sp.[StateProvinceCode] 
    ,sp.[IsOnlyStateProvinceFlag] 
    ,sp.[Name] AS [StateProvinceName] 
    ,sp.[TerritoryID] 
    ,cr.[CountryRegionCode] 
    ,cr.[Name] AS [CountryRegionName]
FROM [Person].[StateProvince] sp 
    INNER JOIN [Person].[CountryRegion] cr 
    ON sp.[CountryRegionCode] = cr.[CountryRegionCode];

--- CONVERTED TARGET CODE (PostgreSQL) — use these exact routine names and signatures in target_sql / call_target ---
CREATE OR REPLACE  VIEW adventureworks_person.vstateprovincecountryregion (stateprovinceid, stateprovincecode, isonlystateprovinceflag, stateprovincename, territoryid, countryregioncode, countryregionname) AS
SELECT
    sp.stateprovinceid, sp.stateprovincecode, sp.isonlystateprovinceflag, sp.name AS stateprovincename, sp.territoryid, cr.countryregioncode, cr.name AS countryregionname
    FROM adventureworks_person.stateprovince AS sp
    INNER JOIN adventureworks_person.countryregion AS cr
        ON LOWER(sp.countryregioncode) = LOWER(cr.countryregioncode);

--- SAMPLED REAL DATA (use these actual values) ---
### CountryRegion  (columns: CountryRegionCode, Name, ModifiedDate)
  AD | Andorra | 2008-04-30 00:00:00
  AE | United Arab Emirates | 2008-04-30 00:00:00
  AF | Afghanistan | 2008-04-30 00:00:00
### EmailAddress  (columns: BusinessEntityID, EmailAddressID, EmailAddress, rowguid, ModifiedDate)
  1 | 1 | ken0@adventure-works.com | 8a1901e4-671b-431a-871c-eadb2942e9ee | 2009-01-07 00:00:00
  2 | 2 | terri0@adventure-works.com | b5ff9efd-72a2-4f87-830b-f338fdd4d162 | 2008-01-24 00:00:00
  3 | 3 | roberto0@adventure-works.com | c8a51084-1c03-4c58-a8b3-55854ae7c499 | 2007-11-04 00:00:00
### Person  (columns: BusinessEntityID, PersonType, NameStyle, Title, FirstName, MiddleName, LastName, Suffix, EmailPromotion, AdditionalContactInfo, Demographics, rowguid, ModifiedDate)
  1 | EM | False |  | Ken | J | Sánchez |  | 0 |  | <IndividualSurvey xmlns="http://schemas.microsoft.com/sqlserver/2004/07/adventur… | 92c4279f-1207-48a3-8448-4636514eb7e2 | 2009-01-07 00:00:00
  2 | EM | False |  | Terri | Lee | Duffy |  | 1 |  | <IndividualSurvey xmlns="http://schemas.microsoft.com/sqlserver/2004/07/adventur… | d8763459-8aa8-47cc-aff7-c9079af79033 | 2008-01-24 00:00:00
  3 | EM | False |  | Roberto |  | Tamburello |  | 0 |  | <IndividualSurvey xmlns="http://schemas.microsoft.com/sqlserver/2004/07/adventur… | e1a2555e-0828-434b-a33b-6f38136a37de | 2007-11-04 00:00:00
### StateProvince  (columns: StateProvinceID, StateProvinceCode, CountryRegionCode, IsOnlyStateProvinceFlag, Name, TerritoryID, rowguid, ModifiedDate)
  1 | AB  | CA | False | Alberta | 6 | 298c2880-ab1c-4982-a5ad-a36eb4ba0d34 | 2014-02-08 10:17:21.587000
  2 | AK  | US | False | Alaska | 1 | 5b7b8462-a888-4e0b-a3e1-7278f8af107e | 2014-02-08 10:17:21.587000
  3 | AL  | US | False | Alabama | 5 | 41b328be-21ae-45d0-841d-6f8dd71ce626 | 2014-02-08 10:17:21.587000
