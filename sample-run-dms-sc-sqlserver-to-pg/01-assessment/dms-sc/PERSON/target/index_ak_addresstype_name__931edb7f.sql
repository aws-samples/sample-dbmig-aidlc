CREATE UNIQUE INDEX ix_addresstype_ak_addresstype_name
ON person.addresstype
USING BTREE (name ASC);