ALTER TABLE adventureworks_humanresources.employee
ADD CONSTRAINT ck_employee_hiredate_1717581157 CHECK (
(hiredate >= '1996-07-01' AND hiredate <= clock_timestamp() + ((1)::NUMERIC || ' DAY')::INTERVAL));