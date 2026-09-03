CREATE UNIQUE INDEX ix_businessentity_ak_businessentity_rowguid
ON person.businessentity
USING BTREE (rowguid ASC);