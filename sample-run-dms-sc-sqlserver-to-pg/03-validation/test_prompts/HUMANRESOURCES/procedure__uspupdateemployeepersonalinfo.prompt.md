<!-- dbmig test-generation prompt  batch 5/5
     Write one test spec (YAML) per object:
       - PROCEDURE HUMANRESOURCES.uspUpdateEmployeePersonalInfo -> tests/HUMANRESOURCES/procedure__uspupdateemployeepersonalinfo.test.yaml
     Then set each unit's status 'generated' in test-manifest-HUMANRESOURCES.yaml. -->

=== CONTEXT ===
Shared tests context for this run: `migrations/<project>/03-validation/_context-tests.md`. Read it once per session if you have not already — it holds the customer-specific rules (highest precedence), datatype map, engine checks and playbook index this task relies on. Do not skip it.

=== TASK — GENERATE EQUIVALENCE TESTS ===
Generate equivalence tests that prove the converted PostgreSQL (Aurora PostgreSQL compatible) procedure `HUMANRESOURCES.uspUpdateEmployeePersonalInfo` behaves the same as the SQL Server source: same input → same return value (functions) or same net effect (procedures). Tests run on BOTH engines and the results are compared. Use the spec format and Rules in the context above.

### PROCEDURE HUMANRESOURCES.uspUpdateEmployeePersonalInfo — write a **procedure**-shape spec
--- SOURCE (PROCEDURE) — HUMANRESOURCES.uspUpdateEmployeePersonalInfo ---
CREATE PROCEDURE [HumanResources].[uspUpdateEmployeePersonalInfo]
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
        UPDATE [HumanResources].[Employee] 
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
-- MANUAL reconversion of HumanResources.uspUpdateEmployeePersonalInfo (7644).
-- EXECUTE AS CALLER dropped: PG procedures are SECURITY INVOKER by default (same effect).
CREATE OR REPLACE PROCEDURE adventureworks_humanresources.uspupdateemployeepersonalinfo(IN par_businessentityid integer, IN par_nationalidnumber character varying, IN par_birthdate timestamp without time zone, IN par_maritalstatus character, IN par_gender character)
 LANGUAGE plpgsql
AS $procedure$
DECLARE
    usplogerror$par_ErrorLogID INTEGER;
    usplogerror$ReturnCode INTEGER;
BEGIN
    UPDATE adventureworks_humanresources.employee
       SET nationalidnumber = par_nationalidnumber, birthdate = par_birthdate,
           maritalstatus = par_maritalstatus, gender = par_gender
     WHERE businessentityid = par_businessentityid;
EXCEPTION
    WHEN OTHERS THEN
        CALL adventureworks_dbo.usplogerror(par_ErrorLogID => usplogerror$par_ErrorLogID, return_code => usplogerror$ReturnCode);
END;
$procedure$;

--- SAMPLED REAL DATA (use these actual values) ---
### Employee  (columns: BusinessEntityID, NationalIDNumber, LoginID, OrganizationNode, OrganizationLevel, JobTitle, BirthDate, MaritalStatus, Gender, HireDate, SalariedFlag, VacationHours, SickLeaveHours, CurrentFlag, rowguid, ModifiedDate)
  1 | 295847284 | adventure-works\ken0 |  |  | Chief Executive Officer | 1969-01-29 | S | M | 2009-01-14 | True | 99 | 69 | True | f01251e5-96a3-448d-981e-0f99d789110d | 2014-06-30 00:00:00
  2 | 245797967 | adventure-works\terri0 | <binary 1 bytes> | 1 | Vice President of Engineering | 1971-08-01 | S | F | 2008-01-31 | True | 1 | 20 | True | 45e8f437-670d-4409-93cb-f9424a40d6ee | 2014-06-30 00:00:00
  3 | 509647174 | adventure-works\roberto0 | <binary 2 bytes> | 2 | Engineering Manager | 1974-11-12 | M | M | 2007-11-11 | True | 2 | 21 | True | 9bbbfb2c-efbb-4217-9ab7-f97689328841 | 2014-06-30 00:00:00
