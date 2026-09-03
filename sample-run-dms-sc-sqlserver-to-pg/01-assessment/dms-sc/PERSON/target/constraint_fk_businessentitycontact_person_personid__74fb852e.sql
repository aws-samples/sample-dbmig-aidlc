ALTER TABLE person.businessentitycontact
ADD CONSTRAINT fk_businessentitycontact_person_personid_747149707 FOREIGN KEY (personid) 
REFERENCES person.person (businessentityid)
ON UPDATE NO ACTION
ON DELETE NO ACTION;