ALTER TABLE humanresources.employeepayhistory
ADD CONSTRAINT fk_employeepayhistory_employee_businessentityid_1003150619 FOREIGN KEY (businessentityid) 
REFERENCES humanresources.employee (businessentityid)
ON UPDATE NO ACTION
ON DELETE NO ACTION;