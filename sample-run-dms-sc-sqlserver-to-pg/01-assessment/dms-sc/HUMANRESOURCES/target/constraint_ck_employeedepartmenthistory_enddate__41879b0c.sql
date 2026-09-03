ALTER TABLE humanresources.employeedepartmenthistory
ADD CONSTRAINT ck_employeedepartmenthistory_enddate_1813581499 CHECK (
(enddate >= startdate OR enddate IS NULL));