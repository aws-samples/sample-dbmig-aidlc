CREATE UNIQUE INDEX ix_addresstype_ak_addresstype_rowguid
ON adventureworks_person.addresstype
USING BTREE (rowguid ASC);