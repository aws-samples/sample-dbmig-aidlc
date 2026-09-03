ALTER TABLE person.personphone
ADD CONSTRAINT fk_personphone_person_businessentityid_1099150961 FOREIGN KEY (businessentityid) 
REFERENCES person.person (businessentityid)
ON UPDATE NO ACTION
ON DELETE NO ACTION;