CREATE UNIQUE INDEX ix_contacttype_ak_contacttype_name
ON person.contacttype
USING BTREE (name ASC);