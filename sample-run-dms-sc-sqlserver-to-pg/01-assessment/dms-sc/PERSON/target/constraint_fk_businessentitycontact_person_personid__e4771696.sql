ALTER TABLE adventureworks_person.businessentitycontact
ADD CONSTRAINT fk_businessentitycontact_person_personid_747149707 FOREIGN KEY (personid) 
REFERENCES adventureworks_person.person (businessentityid)
ON UPDATE NO ACTION
ON DELETE NO ACTION;