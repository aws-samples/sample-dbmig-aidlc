ALTER TABLE person.password
ADD CONSTRAINT fk_password_person_businessentityid_1035150733 FOREIGN KEY (businessentityid) 
REFERENCES person.person (businessentityid)
ON UPDATE NO ACTION
ON DELETE NO ACTION;