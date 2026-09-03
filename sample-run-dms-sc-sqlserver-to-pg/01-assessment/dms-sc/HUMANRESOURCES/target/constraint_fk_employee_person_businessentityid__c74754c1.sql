ALTER TABLE humanresources.employee
ADD CONSTRAINT fk_employee_person_businessentityid_939150391 FOREIGN KEY (businessentityid) 
REFERENCES person.person (businessentityid)
ON UPDATE NO ACTION
ON DELETE NO ACTION;