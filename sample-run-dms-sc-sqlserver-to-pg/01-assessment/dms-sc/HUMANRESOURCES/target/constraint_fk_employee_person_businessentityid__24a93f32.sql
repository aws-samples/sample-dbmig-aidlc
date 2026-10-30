ALTER TABLE adventureworks_humanresources.employee
ADD CONSTRAINT fk_employee_person_businessentityid_939150391 FOREIGN KEY (businessentityid) 
REFERENCES adventureworks_person.person (businessentityid)
ON UPDATE NO ACTION
ON DELETE NO ACTION;