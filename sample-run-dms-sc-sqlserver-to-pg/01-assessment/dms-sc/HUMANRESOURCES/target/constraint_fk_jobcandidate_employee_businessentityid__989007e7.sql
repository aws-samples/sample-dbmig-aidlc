ALTER TABLE humanresources.jobcandidate
ADD CONSTRAINT fk_jobcandidate_employee_businessentityid_1019150676 FOREIGN KEY (businessentityid) 
REFERENCES humanresources.employee (businessentityid)
ON UPDATE NO ACTION
ON DELETE NO ACTION;