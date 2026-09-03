ALTER TABLE humanresources.employee
ADD CONSTRAINT ck_employee_maritalstatus_1701581100 CHECK (
(LOWER(UPPER(maritalstatus)) = LOWER('S') OR LOWER(UPPER(maritalstatus)) = LOWER('M')));