ALTER TABLE adventureworks_person.person
ADD CONSTRAINT fk_person_businessentity_businessentityid_1051150790 FOREIGN KEY (businessentityid) 
REFERENCES adventureworks_person.businessentity (businessentityid)
ON UPDATE NO ACTION
ON DELETE NO ACTION;