-- dbmig target-prep — RECREATE secondary objects AFTER the data load
-- target schema: person   generated: 2026-09-02T07:40:35Z
-- foreign_keys=14 indexes=8 triggers=2  (primary/unique keys are intentionally kept)

-- indexs (8)
CREATE INDEX ix_address_ix_address_stateprovinceid ON person.address USING btree (stateprovinceid);
CREATE INDEX ix_businessentityaddress_ix_businessentityaddress_addressid ON person.businessentityaddress USING btree (addressid);
CREATE INDEX ix_businessentityaddress_ix_businessentityaddress_addresstypeid ON person.businessentityaddress USING btree (addresstypeid);
CREATE INDEX ix_businessentitycontact_ix_businessentitycontact_contacttypeid ON person.businessentitycontact USING btree (contacttypeid);
CREATE INDEX ix_businessentitycontact_ix_businessentitycontact_personid ON person.businessentitycontact USING btree (personid);
CREATE INDEX ix_emailaddress_ix_emailaddress_emailaddress ON person.emailaddress USING btree (emailaddress);
CREATE INDEX ix_person_ix_person_lastname_firstname_middlename ON person.person USING btree (lastname, firstname, middlename);
CREATE INDEX ix_personphone_ix_personphone_phonenumber ON person.personphone USING btree (phonenumber);

-- triggers (2)
CREATE TRIGGER iuperson_after_insert AFTER INSERT ON person.person REFERENCING NEW TABLE AS "inserted$dd8b1d18" FOR EACH STATEMENT EXECUTE FUNCTION person.fn_iuperson();
CREATE TRIGGER iuperson_after_update AFTER UPDATE ON person.person REFERENCING OLD TABLE AS "deleted$dd8b1d18" NEW TABLE AS "inserted$dd8b1d18" FOR EACH STATEMENT EXECUTE FUNCTION person.fn_iuperson();

-- foreign keys (14)
ALTER TABLE "person"."address" ADD CONSTRAINT "fk_address_stateprovince_stateprovinceid_635149308" FOREIGN KEY (stateprovinceid) REFERENCES person.stateprovince(stateprovinceid);
ALTER TABLE "person"."businessentityaddress" ADD CONSTRAINT "fk_businessentityaddress_address_addressid_699149536" FOREIGN KEY (addressid) REFERENCES person.address(addressid);
ALTER TABLE "person"."businessentityaddress" ADD CONSTRAINT "fk_businessentityaddress_addresstype_addresstypeid_715149593" FOREIGN KEY (addresstypeid) REFERENCES person.addresstype(addresstypeid);
ALTER TABLE "person"."businessentityaddress" ADD CONSTRAINT "fk_businessentityaddress_businessentity_businessentityid_731149" FOREIGN KEY (businessentityid) REFERENCES person.businessentity(businessentityid);
ALTER TABLE "person"."businessentitycontact" ADD CONSTRAINT "fk_businessentitycontact_businessentity_businessentityid_779149" FOREIGN KEY (businessentityid) REFERENCES person.businessentity(businessentityid);
ALTER TABLE "person"."businessentitycontact" ADD CONSTRAINT "fk_businessentitycontact_contacttype_contacttypeid_763149764" FOREIGN KEY (contacttypeid) REFERENCES person.contacttype(contacttypeid);
ALTER TABLE "person"."businessentitycontact" ADD CONSTRAINT "fk_businessentitycontact_person_personid_747149707" FOREIGN KEY (personid) REFERENCES person.person(businessentityid);
ALTER TABLE "person"."emailaddress" ADD CONSTRAINT "fk_emailaddress_person_businessentityid_923150334" FOREIGN KEY (businessentityid) REFERENCES person.person(businessentityid);
ALTER TABLE "person"."password" ADD CONSTRAINT "fk_password_person_businessentityid_1035150733" FOREIGN KEY (businessentityid) REFERENCES person.person(businessentityid);
ALTER TABLE "person"."person" ADD CONSTRAINT "fk_person_businessentity_businessentityid_1051150790" FOREIGN KEY (businessentityid) REFERENCES person.businessentity(businessentityid);
ALTER TABLE "person"."personphone" ADD CONSTRAINT "fk_personphone_person_businessentityid_1099150961" FOREIGN KEY (businessentityid) REFERENCES person.person(businessentityid);
ALTER TABLE "person"."personphone" ADD CONSTRAINT "fk_personphone_phonenumbertype_phonenumbertypeid_1115151018" FOREIGN KEY (phonenumbertypeid) REFERENCES person.phonenumbertype(phonenumbertypeid);
ALTER TABLE "person"."stateprovince" ADD CONSTRAINT "fk_stateprovince_countryregion_countryregioncode_1915153868" FOREIGN KEY (countryregioncode) REFERENCES person.countryregion(countryregioncode);
ALTER TABLE "person"."stateprovince" ADD CONSTRAINT "fk_stateprovince_salesterritory_territoryid_1931153925" FOREIGN KEY (territoryid) REFERENCES sales.salesterritory(territoryid);
