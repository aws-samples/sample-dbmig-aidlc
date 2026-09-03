ALTER TABLE humanresources.employee
ADD CONSTRAINT ck_employee_birthdate_1685581043 CHECK (
(birthdate >= '1930-01-01' AND birthdate <= clock_timestamp() + ((- 18)::NUMERIC || ' YEAR')::INTERVAL));