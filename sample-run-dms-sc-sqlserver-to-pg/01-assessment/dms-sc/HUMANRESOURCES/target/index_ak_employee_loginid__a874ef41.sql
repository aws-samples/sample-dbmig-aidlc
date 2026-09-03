CREATE UNIQUE INDEX ix_employee_ak_employee_loginid
ON humanresources.employee
USING BTREE (loginid ASC);