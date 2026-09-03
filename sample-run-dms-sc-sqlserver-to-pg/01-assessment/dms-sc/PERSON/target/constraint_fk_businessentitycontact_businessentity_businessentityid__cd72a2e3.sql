ALTER TABLE person.businessentitycontact
ADD CONSTRAINT fk_businessentitycontact_businessentity_businessentityid_779149821 FOREIGN KEY (businessentityid) 
REFERENCES person.businessentity (businessentityid)
ON UPDATE NO ACTION
ON DELETE NO ACTION;