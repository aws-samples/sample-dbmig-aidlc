ALTER TABLE person.businessentitycontact
ADD CONSTRAINT fk_businessentitycontact_contacttype_contacttypeid_763149764 FOREIGN KEY (contacttypeid) 
REFERENCES person.contacttype (contacttypeid)
ON UPDATE NO ACTION
ON DELETE NO ACTION;