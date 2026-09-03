ALTER TABLE person.emailaddress
ADD CONSTRAINT fk_emailaddress_person_businessentityid_923150334 FOREIGN KEY (businessentityid) 
REFERENCES person.person (businessentityid)
ON UPDATE NO ACTION
ON DELETE NO ACTION;