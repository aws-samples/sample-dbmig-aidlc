CREATE UNIQUE INDEX ix_address_ak_address_rowguid
ON person.address
USING BTREE (rowguid ASC);