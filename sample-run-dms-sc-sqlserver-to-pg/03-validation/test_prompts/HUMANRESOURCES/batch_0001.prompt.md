<!-- dbmig test-generation prompt  batch 1/5
     Write one test spec (YAML) per object:
       - VIEW HUMANRESOURCES.vEmployee -> tests/HUMANRESOURCES/view__vemployee.test.yaml
       - VIEW HUMANRESOURCES.vEmployeeDepartment -> tests/HUMANRESOURCES/view__vemployeedepartment.test.yaml
       - VIEW HUMANRESOURCES.vEmployeeDepartmentHistory -> tests/HUMANRESOURCES/view__vemployeedepartmenthistory.test.yaml
     Then set each unit's status 'generated' in test-manifest-HUMANRESOURCES.yaml. -->

=== CONTEXT ===
Shared tests context for this run: `migrations/<project>/03-validation/_context-tests.md`. Read it once per session if you have not already — it holds the customer-specific rules (highest precedence), datatype map, engine checks and playbook index this task relies on. Do not skip it.

=== TASK — GENERATE EQUIVALENCE TESTS ===
Generate equivalence tests that prove each of the 3 converted PostgreSQL (Aurora PostgreSQL compatible) objects below (one spec file per object, as listed in the header) behaves the same as the SQL Server source: same input → same return value (functions) or same net effect (procedures). Tests run on BOTH engines and the results are compared. Use the spec format and Rules in the context above.

### VIEW HUMANRESOURCES.vEmployee — write a **function and/or procedure**-shape spec
--- SOURCE (VIEW) — HUMANRESOURCES.vEmployee ---
CREATE VIEW [HumanResources].[vEmployee] 
AS 
SELECT 
    e.[BusinessEntityID]
    ,p.[Title]
    ,p.[FirstName]
    ,p.[MiddleName]
    ,p.[LastName]
    ,p.[Suffix]
    ,e.[JobTitle]  
    ,pp.[PhoneNumber]
    ,pnt.[Name] AS [PhoneNumberType]
    ,ea.[EmailAddress]
    ,p.[EmailPromotion]
    ,a.[AddressLine1]
    ,a.[AddressLine2]
    ,a.[City]
    ,sp.[Name] AS [StateProvinceName] 
    ,a.[PostalCode]
    ,cr.[Name] AS [CountryRegionName] 
    ,p.[AdditionalContactInfo]
FROM [HumanResources].[Employee] e
	INNER JOIN [Person].[Person] p
	ON p.[BusinessEntityID] = e.[BusinessEntityID]
    INNER JOIN [Person].[BusinessEntityAddress] bea 
    ON bea.[BusinessEntityID] = e.[BusinessEntityID] 
    INNER JOIN [Person].[Address] a 
    ON a.[AddressID] = bea.[AddressID]
    INNER JOIN [Person].[StateProvince] sp 
    ON sp.[StateProvinceID] = a.[StateProvinceID]
    INNER JOIN [Person].[CountryRegion] cr 
    ON cr.[CountryRegionCode] = sp.[CountryRegionCode]
    LEFT OUTER JOIN [Person].[PersonPhone] pp
    ON pp.BusinessEntityID = p.[BusinessEntityID]
    LEFT OUTER JOIN [Person].[PhoneNumberType] pnt
    ON pp.[PhoneNumberTypeID] = pnt.[PhoneNumberTypeID]
    LEFT OUTER JOIN [Person].[EmailAddress] ea
    ON p.[BusinessEntityID] = ea.[BusinessEntityID];

--- CONVERTED TARGET CODE (PostgreSQL) — use these exact routine names and signatures in target_sql / call_target ---
CREATE OR REPLACE  VIEW adventureworks_humanresources.vemployee (businessentityid, title, firstname, middlename, lastname, suffix, jobtitle, phonenumber, phonenumbertype, emailaddress, emailpromotion, addressline1, addressline2, city, stateprovincename, postalcode, countryregionname, additionalcontactinfo) AS
SELECT
    e.businessentityid, p.title, p.firstname, p.middlename, p.lastname, p.suffix, e.jobtitle, pp.phonenumber, pnt.name AS phonenumbertype, ea.emailaddress, p.emailpromotion, a.addressline1, a.addressline2, a.city, sp.name AS stateprovincename, a.postalcode, cr.name AS countryregionname, p.additionalcontactinfo
    FROM adventureworks_humanresources.employee AS e
    INNER JOIN adventureworks_person.person AS p
        ON p.businessentityid = e.businessentityid
    INNER JOIN adventureworks_person.businessentityaddress AS bea
        ON bea.businessentityid = e.businessentityid
    INNER JOIN adventureworks_person.address AS a
        ON a.addressid = bea.addressid
    INNER JOIN adventureworks_person.stateprovince AS sp
        ON sp.stateprovinceid = a.stateprovinceid
    INNER JOIN adventureworks_person.countryregion AS cr
        ON LOWER(cr.countryregioncode) = LOWER(sp.countryregioncode)
    LEFT OUTER JOIN adventureworks_person.personphone AS pp
        ON pp.businessentityid = p.businessentityid
    LEFT OUTER JOIN adventureworks_person.phonenumbertype AS pnt
        ON pp.phonenumbertypeid = pnt.phonenumbertypeid
    LEFT OUTER JOIN adventureworks_person.emailaddress AS ea
        ON p.businessentityid = ea.businessentityid;

### VIEW HUMANRESOURCES.vEmployeeDepartment — write a **function and/or procedure**-shape spec
--- SOURCE (VIEW) — HUMANRESOURCES.vEmployeeDepartment ---
CREATE VIEW [HumanResources].[vEmployeeDepartment] 
AS 
SELECT 
    e.[BusinessEntityID] 
    ,p.[Title] 
    ,p.[FirstName] 
    ,p.[MiddleName] 
    ,p.[LastName] 
    ,p.[Suffix] 
    ,e.[JobTitle]
    ,d.[Name] AS [Department] 
    ,d.[GroupName] 
    ,edh.[StartDate] 
FROM [HumanResources].[Employee] e
	INNER JOIN [Person].[Person] p
	ON p.[BusinessEntityID] = e.[BusinessEntityID]
    INNER JOIN [HumanResources].[EmployeeDepartmentHistory] edh 
    ON e.[BusinessEntityID] = edh.[BusinessEntityID] 
    INNER JOIN [HumanResources].[Department] d 
    ON edh.[DepartmentID] = d.[DepartmentID] 
WHERE edh.EndDate IS NULL

--- CONVERTED TARGET CODE (PostgreSQL) — use these exact routine names and signatures in target_sql / call_target ---
CREATE OR REPLACE  VIEW adventureworks_humanresources.vemployeedepartment (businessentityid, title, firstname, middlename, lastname, suffix, jobtitle, department, groupname, startdate) AS
SELECT
    e.businessentityid, p.title, p.firstname, p.middlename, p.lastname, p.suffix, e.jobtitle, d.name AS department, d.groupname, edh.startdate
    FROM adventureworks_humanresources.employee AS e
    INNER JOIN adventureworks_person.person AS p
        ON p.businessentityid = e.businessentityid
    INNER JOIN adventureworks_humanresources.employeedepartmenthistory AS edh
        ON e.businessentityid = edh.businessentityid
    INNER JOIN adventureworks_humanresources.department AS d
        ON edh.departmentid = d.departmentid
    WHERE edh.enddate IS NULL;

### VIEW HUMANRESOURCES.vEmployeeDepartmentHistory — write a **function and/or procedure**-shape spec
--- SOURCE (VIEW) — HUMANRESOURCES.vEmployeeDepartmentHistory ---
CREATE VIEW [HumanResources].[vEmployeeDepartmentHistory] 
AS 
SELECT 
    e.[BusinessEntityID] 
    ,p.[Title] 
    ,p.[FirstName] 
    ,p.[MiddleName] 
    ,p.[LastName] 
    ,p.[Suffix] 
    ,s.[Name] AS [Shift]
    ,d.[Name] AS [Department] 
    ,d.[GroupName] 
    ,edh.[StartDate] 
    ,edh.[EndDate]
FROM [HumanResources].[Employee] e
	INNER JOIN [Person].[Person] p
	ON p.[BusinessEntityID] = e.[BusinessEntityID]
    INNER JOIN [HumanResources].[EmployeeDepartmentHistory] edh 
    ON e.[BusinessEntityID] = edh.[BusinessEntityID] 
    INNER JOIN [HumanResources].[Department] d 
    ON edh.[DepartmentID] = d.[DepartmentID] 
    INNER JOIN [HumanResources].[Shift] s
    ON s.[ShiftID] = edh.[ShiftID];

--- CONVERTED TARGET CODE (PostgreSQL) — use these exact routine names and signatures in target_sql / call_target ---
CREATE OR REPLACE  VIEW adventureworks_humanresources.vemployeedepartmenthistory (businessentityid, title, firstname, middlename, lastname, suffix, shift, department, groupname, startdate, enddate) AS
SELECT
    e.businessentityid, p.title, p.firstname, p.middlename, p.lastname, p.suffix, s.name AS shift, d.name AS department, d.groupname, edh.startdate, edh.enddate
    FROM adventureworks_humanresources.employee AS e
    INNER JOIN adventureworks_person.person AS p
        ON p.businessentityid = e.businessentityid
    INNER JOIN adventureworks_humanresources.employeedepartmenthistory AS edh
        ON e.businessentityid = edh.businessentityid
    INNER JOIN adventureworks_humanresources.department AS d
        ON edh.departmentid = d.departmentid
    INNER JOIN adventureworks_humanresources.shift AS s
        ON s.shiftid = edh.shiftid;

--- SAMPLED REAL DATA (use these actual values) ---
### Employee  (columns: BusinessEntityID, NationalIDNumber, LoginID, OrganizationNode, OrganizationLevel, JobTitle, BirthDate, MaritalStatus, Gender, HireDate, SalariedFlag, VacationHours, SickLeaveHours, CurrentFlag, rowguid, ModifiedDate)
  1 | 295847284 | adventure-works\ken0 |  |  | Chief Executive Officer | 1969-01-29 | S | M | 2009-01-14 | True | 99 | 69 | True | f01251e5-96a3-448d-981e-0f99d789110d | 2014-06-30 00:00:00
  2 | 245797967 | adventure-works\terri0 | <binary 1 bytes> | 1 | Vice President of Engineering | 1971-08-01 | S | F | 2008-01-31 | True | 1 | 20 | True | 45e8f437-670d-4409-93cb-f9424a40d6ee | 2014-06-30 00:00:00
  3 | 509647174 | adventure-works\roberto0 | <binary 2 bytes> | 2 | Engineering Manager | 1974-11-12 | M | M | 2007-11-11 | True | 2 | 21 | True | 9bbbfb2c-efbb-4217-9ab7-f97689328841 | 2014-06-30 00:00:00
### Department  (columns: DepartmentID, Name, GroupName, ModifiedDate)
  1 | Engineering | Research and Development | 2008-04-30 00:00:00
  2 | Tool Design | Research and Development | 2008-04-30 00:00:00
  3 | Sales | Sales and Marketing | 2008-04-30 00:00:00
### EmployeeDepartmentHistory  (columns: BusinessEntityID, DepartmentID, ShiftID, StartDate, EndDate, ModifiedDate)
  1 | 16 | 1 | 2009-01-14 |  | 2009-01-13 00:00:00
  2 | 1 | 1 | 2008-01-31 |  | 2008-01-30 00:00:00
  3 | 1 | 1 | 2007-11-11 |  | 2007-11-10 00:00:00
### Shift  (columns: ShiftID, Name, StartTime, EndTime, ModifiedDate)
  1 | Day | 07:00:00 | 15:00:00 | 2008-04-30 00:00:00
  2 | Evening | 15:00:00 | 23:00:00 | 2008-04-30 00:00:00
  3 | Night | 23:00:00 | 07:00:00 | 2008-04-30 00:00:00
