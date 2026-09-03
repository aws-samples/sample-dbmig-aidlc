ALTER TABLE humanresources.employee
ADD CONSTRAINT ck_employee_vacationhours_1749581271 CHECK (
(vacationhours >= (- 40) AND vacationhours <= (240)));