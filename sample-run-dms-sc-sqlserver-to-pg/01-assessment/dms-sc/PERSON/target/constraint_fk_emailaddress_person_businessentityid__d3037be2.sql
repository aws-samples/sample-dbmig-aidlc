ALTER TABLE adventureworks_person.emailaddress
ADD CONSTRAINT fk_emailaddress_person_businessentityid_923150334 FOREIGN KEY (businessentityid) 
REFERENCES adventureworks_person.person (businessentityid)
ON UPDATE NO ACTION
ON DELETE NO ACTION;