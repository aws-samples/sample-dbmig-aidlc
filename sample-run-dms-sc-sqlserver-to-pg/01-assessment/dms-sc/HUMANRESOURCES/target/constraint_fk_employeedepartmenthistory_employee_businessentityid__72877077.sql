ALTER TABLE humanresources.employeedepartmenthistory
ADD CONSTRAINT fk_employeedepartmenthistory_employee_businessentityid_971150505 FOREIGN KEY (businessentityid) 
REFERENCES humanresources.employee (businessentityid)
ON UPDATE NO ACTION
ON DELETE NO ACTION;