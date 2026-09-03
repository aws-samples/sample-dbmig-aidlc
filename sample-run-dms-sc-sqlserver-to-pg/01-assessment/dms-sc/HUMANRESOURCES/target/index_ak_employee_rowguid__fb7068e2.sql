CREATE UNIQUE INDEX ix_employee_ak_employee_rowguid
ON humanresources.employee
USING BTREE (rowguid ASC);