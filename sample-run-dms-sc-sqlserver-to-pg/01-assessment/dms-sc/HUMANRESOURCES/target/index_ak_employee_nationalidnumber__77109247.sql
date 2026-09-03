CREATE UNIQUE INDEX ix_employee_ak_employee_nationalidnumber
ON humanresources.employee
USING BTREE (nationalidnumber ASC);