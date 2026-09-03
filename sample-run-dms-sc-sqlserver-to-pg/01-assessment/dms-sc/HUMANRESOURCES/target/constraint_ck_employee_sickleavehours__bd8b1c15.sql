ALTER TABLE humanresources.employee
ADD CONSTRAINT ck_employee_sickleavehours_1765581328 CHECK (
(sickleavehours >= (0) AND sickleavehours <= (120)));