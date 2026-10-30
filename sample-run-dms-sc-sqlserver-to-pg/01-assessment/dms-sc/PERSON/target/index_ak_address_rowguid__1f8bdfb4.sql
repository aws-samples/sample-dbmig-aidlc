CREATE UNIQUE INDEX ix_address_ak_address_rowguid
ON adventureworks_person.address
USING BTREE (rowguid ASC);