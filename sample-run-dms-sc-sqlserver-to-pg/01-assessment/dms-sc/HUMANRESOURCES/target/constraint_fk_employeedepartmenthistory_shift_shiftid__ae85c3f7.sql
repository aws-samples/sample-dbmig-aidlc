ALTER TABLE humanresources.employeedepartmenthistory
ADD CONSTRAINT fk_employeedepartmenthistory_shift_shiftid_987150562 FOREIGN KEY (shiftid) 
REFERENCES humanresources.shift (shiftid)
ON UPDATE NO ACTION
ON DELETE NO ACTION;