ALTER TABLE humanresources.employee
ADD CONSTRAINT ck_employee_gender_1733581214 CHECK (
(LOWER(UPPER(gender)) = LOWER('F') OR LOWER(UPPER(gender)) = LOWER('M')));