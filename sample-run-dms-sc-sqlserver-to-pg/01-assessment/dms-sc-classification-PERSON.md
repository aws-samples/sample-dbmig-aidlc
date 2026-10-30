# DMS SC import — triage for schema `PERSON`

- Project: **aw-dms-sc-20261030**
- Source: **MSSQL** → Target: **AURORA_POSTGRESQL** (target schema `adventureworks_person`)
- Objects: **76** (storage=71, code=3, other=2)

## Disposition

| Disposition | Count | Meaning |
|---|---|---|
| ACCEPT | 51 | keep the DMS SC conversion as-is |
| VERIFY | 20 | keep, but prove with equivalence tests (gen-tests/run-tests) |
| MANUAL | 5 | must be reconverted (convert-code) |

> **Policy:** MANUAL = any action item of severity CRITICAL/HIGH, or an explicit "convert your source code manually" / method-stub instruction. VERIFY = any remaining action item (incl. `5444` ML/GenAI and LOW/MEDIUM advisories) or a GenAI-generated span. ACCEPT = no action items. Tune in `dbmig/dmssc/classify.py`.

## MANUAL — reconvert (5)

| Object | Type | GenAI | Applied | Action items |
|---|---|---|---|---|
| `Person.IX_vStateProvinceCountryRegion` | INDEX | - | - | 7937/CRITICAL Convert your source code manually. |
| `Person.iuPerson` | TRIGGER | - | SUCCESS | 7833/CRITICAL Convert your source code manually.; 9997/INFO Verify the object name and conversion scope, grant the source database user access if needed, and reconvert. Review runtime-built or unsupported references manually.; 7708/CRITICAL Convert your source code manually. |
| `Person.vAdditionalContactInfo` | VIEW | - | SUCCESS | 7708/CRITICAL Convert your source code manually. |
| `Person.AdditionalContactInfoSchemaCollection` | XML_SCHEMA_COLLECTION | - | - | 9994/CRITICAL Perform manual conversion. |
| `Person.IndividualSurveySchemaCollection` | XML_SCHEMA_COLLECTION | - | - | 9994/CRITICAL Perform manual conversion. |

## VERIFY — keep + prove (20)

| Object | Type | Verified | GenAI | Applied | Action items |
|---|---|---|---|---|---|
| `Person.CK_Person_PersonType` | CONSTRAINT | ✅ verified | - | SUCCESS | 7795/INFO Review the converted code to make sure that it compares strings correctly. |
| `Person.PXML_Person_AddContact` | INDEX | ❌ failed | - | ERROR | 7791/INFO No action required. The index works identically; it just isn’t compressed. If compression matters, evaluate PostgreSQL options separately. |
| `Person.PXML_Person_Demographics` | INDEX | ❌ failed | - | ERROR | 7791/INFO No action required. The index works identically; it just isn’t compressed. If compression matters, evaluate PostgreSQL options separately. |
| `Person.XMLPATH_Person_Demographics` | INDEX | ❌ failed | - | ERROR | 7791/INFO No action required. The index works identically; it just isn’t compressed. If compression matters, evaluate PostgreSQL options separately. |
| `Person.XMLPROPERTY_Person_Demographics` | INDEX | ❌ failed | - | ERROR | 7791/INFO No action required. The index works identically; it just isn’t compressed. If compression matters, evaluate PostgreSQL options separately. |
| `Person.XMLVALUE_Person_Demographics` | INDEX | ❌ failed | - | ERROR | 7791/INFO No action required. The index works identically; it just isn’t compressed. If compression matters, evaluate PostgreSQL options separately. |
| `Person.Address` | TABLE | ✅ verified | - | SUCCESS | 7831/INFO Revise your database settings and try again.; 7826/LOW Review the converted code to make sure that you set the default value of the DateTime variable. |
| `Person.AddressType` | TABLE | ✅ verified | - | SUCCESS | 7831/INFO Revise your database settings and try again.; 7826/LOW Review the converted code to make sure that you set the default value of the DateTime variable. |
| `Person.BusinessEntity` | TABLE | ✅ verified | - | SUCCESS | 7831/INFO Revise your database settings and try again.; 7826/LOW Review the converted code to make sure that you set the default value of the DateTime variable. |
| `Person.BusinessEntityAddress` | TABLE | ✅ verified | - | SUCCESS | 7831/INFO Revise your database settings and try again.; 7826/LOW Review the converted code to make sure that you set the default value of the DateTime variable. |
| `Person.BusinessEntityContact` | TABLE | ✅ verified | - | SUCCESS | 7831/INFO Revise your database settings and try again.; 7826/LOW Review the converted code to make sure that you set the default value of the DateTime variable. |
| `Person.ContactType` | TABLE | ✅ verified | - | SUCCESS | 7826/LOW Review the converted code to make sure that you set the default value of the DateTime variable. |
| `Person.CountryRegion` | TABLE | ✅ verified | - | SUCCESS | 7826/LOW Review the converted code to make sure that you set the default value of the DateTime variable. |
| `Person.EmailAddress` | TABLE | ✅ verified | - | SUCCESS | 7831/INFO Revise your database settings and try again.; 7826/LOW Review the converted code to make sure that you set the default value of the DateTime variable. |
| `Person.Password` | TABLE | ✅ verified | - | SUCCESS | 7831/INFO Revise your database settings and try again.; 7826/LOW Review the converted code to make sure that you set the default value of the DateTime variable. |
| `Person.Person` | TABLE | ✅ verified | - | SUCCESS | 7831/INFO Revise your database settings and try again.; 7826/LOW Review the converted code to make sure that you set the default value of the DateTime variable. |
| `Person.PersonPhone` | TABLE | ✅ verified | - | SUCCESS | 7826/LOW Review the converted code to make sure that you set the default value of the DateTime variable. |
| `Person.PhoneNumberType` | TABLE | ✅ verified | - | SUCCESS | 7826/LOW Review the converted code to make sure that you set the default value of the DateTime variable. |
| `Person.StateProvince` | TABLE | ✅ verified | - | SUCCESS | 7831/INFO Revise your database settings and try again.; 7826/LOW Review the converted code to make sure that you set the default value of the DateTime variable. |
| `Person.vStateProvinceCountryRegion` | VIEW | ✅ verified | - | SUCCESS | 7795/INFO Review the converted code to make sure that it compares strings correctly.; 7634/INFO Revise your code to avoid using SCHEMABINDING and try again. |

## ACCEPT — keep as-is (51)

| Object | Type | Applied |
|---|---|---|
| `Person.CK_Person_EmailPromotion` | CONSTRAINT | SUCCESS |
| `Person.FK_Address_StateProvince_StateProvinceID` | CONSTRAINT | SUCCESS |
| `Person.FK_BusinessEntityAddress_AddressType_AddressTypeID` | CONSTRAINT | SUCCESS |
| `Person.FK_BusinessEntityAddress_Address_AddressID` | CONSTRAINT | SUCCESS |
| `Person.FK_BusinessEntityAddress_BusinessEntity_BusinessEntityID` | CONSTRAINT | SUCCESS |
| `Person.FK_BusinessEntityContact_BusinessEntity_BusinessEntityID` | CONSTRAINT | SUCCESS |
| `Person.FK_BusinessEntityContact_ContactType_ContactTypeID` | CONSTRAINT | SUCCESS |
| `Person.FK_BusinessEntityContact_Person_PersonID` | CONSTRAINT | SUCCESS |
| `Person.FK_EmailAddress_Person_BusinessEntityID` | CONSTRAINT | SUCCESS |
| `Person.FK_Password_Person_BusinessEntityID` | CONSTRAINT | SUCCESS |
| `Person.FK_PersonPhone_Person_BusinessEntityID` | CONSTRAINT | SUCCESS |
| `Person.FK_PersonPhone_PhoneNumberType_PhoneNumberTypeID` | CONSTRAINT | SUCCESS |
| `Person.FK_Person_BusinessEntity_BusinessEntityID` | CONSTRAINT | SUCCESS |
| `Person.FK_StateProvince_CountryRegion_CountryRegionCode` | CONSTRAINT | SUCCESS |
| `Person.FK_StateProvince_SalesTerritory_TerritoryID` | CONSTRAINT | ERROR |
| `Person.PK_AddressType_AddressTypeID` | CONSTRAINT | SUCCESS |
| `Person.PK_Address_AddressID` | CONSTRAINT | SUCCESS |
| `Person.PK_BusinessEntityAddress_BusinessEntityID_AddressID_AddressTypeID` | CONSTRAINT | SUCCESS |
| `Person.PK_BusinessEntityContact_BusinessEntityID_PersonID_ContactTypeID` | CONSTRAINT | SUCCESS |
| `Person.PK_BusinessEntity_BusinessEntityID` | CONSTRAINT | SUCCESS |
| `Person.PK_ContactType_ContactTypeID` | CONSTRAINT | SUCCESS |
| `Person.PK_CountryRegion_CountryRegionCode` | CONSTRAINT | SUCCESS |
| `Person.PK_EmailAddress_BusinessEntityID_EmailAddressID` | CONSTRAINT | SUCCESS |
| `Person.PK_Password_BusinessEntityID` | CONSTRAINT | SUCCESS |
| `Person.PK_PersonPhone_BusinessEntityID_PhoneNumber_PhoneNumberTypeID` | CONSTRAINT | SUCCESS |
| `Person.PK_Person_BusinessEntityID` | CONSTRAINT | SUCCESS |
| `Person.PK_PhoneNumberType_PhoneNumberTypeID` | CONSTRAINT | SUCCESS |
| `Person.PK_StateProvince_StateProvinceID` | CONSTRAINT | SUCCESS |
| `Person.AK_AddressType_Name` | INDEX | SUCCESS |
| `Person.AK_AddressType_rowguid` | INDEX | SUCCESS |
| `Person.AK_Address_rowguid` | INDEX | SUCCESS |
| `Person.AK_BusinessEntityAddress_rowguid` | INDEX | SUCCESS |
| `Person.AK_BusinessEntityContact_rowguid` | INDEX | SUCCESS |
| `Person.AK_BusinessEntity_rowguid` | INDEX | SUCCESS |
| `Person.AK_ContactType_Name` | INDEX | SUCCESS |
| `Person.AK_CountryRegion_Name` | INDEX | SUCCESS |
| `Person.AK_Person_rowguid` | INDEX | SUCCESS |
| `Person.AK_StateProvince_Name` | INDEX | SUCCESS |
| `Person.AK_StateProvince_StateProvinceCode_CountryRegionCode` | INDEX | SUCCESS |
| `Person.AK_StateProvince_rowguid` | INDEX | SUCCESS |
| `Person.IX_Address_AddressLine1_AddressLine2_City_StateProvinceID_PostalCode` | INDEX | SUCCESS |
| `Person.IX_Address_StateProvinceID` | INDEX | SUCCESS |
| `Person.IX_BusinessEntityAddress_AddressID` | INDEX | SUCCESS |
| `Person.IX_BusinessEntityAddress_AddressTypeID` | INDEX | SUCCESS |
| `Person.IX_BusinessEntityContact_ContactTypeID` | INDEX | SUCCESS |
| `Person.IX_BusinessEntityContact_PersonID` | INDEX | SUCCESS |
| `Person.IX_EmailAddress_EmailAddress` | INDEX | SUCCESS |
| `Person.IX_PersonPhone_PhoneNumber` | INDEX | SUCCESS |
| `Person.IX_Person_LastName_FirstName_MiddleName` | INDEX | SUCCESS |
| `Person.Namespaces` | NAMESPACES | - |
| `Person.Namespaces` | NAMESPACES | - |

