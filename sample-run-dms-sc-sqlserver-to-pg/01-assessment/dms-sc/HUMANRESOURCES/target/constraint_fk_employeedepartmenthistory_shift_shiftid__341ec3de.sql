ALTER TABLE adventureworks_humanresources.employeedepartmenthistory
ADD CONSTRAINT fk_employeedepartmenthistory_shift_shiftid_987150562 FOREIGN KEY (shiftid) 
REFERENCES adventureworks_humanresources.shift (shiftid)
ON UPDATE NO ACTION
ON DELETE NO ACTION;