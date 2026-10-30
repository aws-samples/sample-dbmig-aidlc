CREATE UNIQUE INDEX ix_department_ak_department_name
ON adventureworks_humanresources.department
USING BTREE (name ASC);