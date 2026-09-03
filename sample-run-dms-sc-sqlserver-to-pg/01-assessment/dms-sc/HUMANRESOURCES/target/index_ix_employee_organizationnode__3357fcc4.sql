CREATE INDEX ix_employee_ix_employee_organizationnode
ON humanresources.employee
USING BTREE (organizationnode ASC);