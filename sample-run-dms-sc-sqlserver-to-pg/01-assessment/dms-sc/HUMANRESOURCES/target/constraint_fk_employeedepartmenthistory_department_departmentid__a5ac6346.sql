ALTER TABLE humanresources.employeedepartmenthistory
ADD CONSTRAINT fk_employeedepartmenthistory_department_departmentid_955150448 FOREIGN KEY (departmentid) 
REFERENCES humanresources.department (departmentid)
ON UPDATE NO ACTION
ON DELETE NO ACTION;