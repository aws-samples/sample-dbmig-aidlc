CREATE UNIQUE INDEX ix_department_ak_department_name
ON humanresources.department
USING BTREE (name ASC);