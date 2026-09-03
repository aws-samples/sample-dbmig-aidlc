-- dbmig target-prep — DROP secondary objects BEFORE the data load
-- target schema: person   generated: 2026-09-02T07:40:35Z
-- foreign_keys=14 indexes=8 triggers=2  (primary/unique keys are intentionally kept)

-- foreign keys (14)
ALTER TABLE "person"."address" DROP CONSTRAINT IF EXISTS "fk_address_stateprovince_stateprovinceid_635149308";
ALTER TABLE "person"."businessentityaddress" DROP CONSTRAINT IF EXISTS "fk_businessentityaddress_address_addressid_699149536";
ALTER TABLE "person"."businessentityaddress" DROP CONSTRAINT IF EXISTS "fk_businessentityaddress_addresstype_addresstypeid_715149593";
ALTER TABLE "person"."businessentityaddress" DROP CONSTRAINT IF EXISTS "fk_businessentityaddress_businessentity_businessentityid_731149";
ALTER TABLE "person"."businessentitycontact" DROP CONSTRAINT IF EXISTS "fk_businessentitycontact_businessentity_businessentityid_779149";
ALTER TABLE "person"."businessentitycontact" DROP CONSTRAINT IF EXISTS "fk_businessentitycontact_contacttype_contacttypeid_763149764";
ALTER TABLE "person"."businessentitycontact" DROP CONSTRAINT IF EXISTS "fk_businessentitycontact_person_personid_747149707";
ALTER TABLE "person"."emailaddress" DROP CONSTRAINT IF EXISTS "fk_emailaddress_person_businessentityid_923150334";
ALTER TABLE "person"."password" DROP CONSTRAINT IF EXISTS "fk_password_person_businessentityid_1035150733";
ALTER TABLE "person"."person" DROP CONSTRAINT IF EXISTS "fk_person_businessentity_businessentityid_1051150790";
ALTER TABLE "person"."personphone" DROP CONSTRAINT IF EXISTS "fk_personphone_person_businessentityid_1099150961";
ALTER TABLE "person"."personphone" DROP CONSTRAINT IF EXISTS "fk_personphone_phonenumbertype_phonenumbertypeid_1115151018";
ALTER TABLE "person"."stateprovince" DROP CONSTRAINT IF EXISTS "fk_stateprovince_countryregion_countryregioncode_1915153868";
ALTER TABLE "person"."stateprovince" DROP CONSTRAINT IF EXISTS "fk_stateprovince_salesterritory_territoryid_1931153925";

-- triggers (2)
DROP TRIGGER IF EXISTS "iuperson_after_insert" ON "person"."person";
DROP TRIGGER IF EXISTS "iuperson_after_update" ON "person"."person";

-- indexs (8)
DROP INDEX IF EXISTS "person"."ix_address_ix_address_stateprovinceid";
DROP INDEX IF EXISTS "person"."ix_businessentityaddress_ix_businessentityaddress_addressid";
DROP INDEX IF EXISTS "person"."ix_businessentityaddress_ix_businessentityaddress_addresstypeid";
DROP INDEX IF EXISTS "person"."ix_businessentitycontact_ix_businessentitycontact_contacttypeid";
DROP INDEX IF EXISTS "person"."ix_businessentitycontact_ix_businessentitycontact_personid";
DROP INDEX IF EXISTS "person"."ix_emailaddress_ix_emailaddress_emailaddress";
DROP INDEX IF EXISTS "person"."ix_person_ix_person_lastname_firstname_middlename";
DROP INDEX IF EXISTS "person"."ix_personphone_ix_personphone_phonenumber";
