CREATE UNIQUE INDEX ix_addresstype_ak_addresstype_rowguid
ON person.addresstype
USING BTREE (rowguid ASC);