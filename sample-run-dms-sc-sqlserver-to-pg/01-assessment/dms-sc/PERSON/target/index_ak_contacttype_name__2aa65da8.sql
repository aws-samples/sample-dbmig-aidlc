CREATE UNIQUE INDEX ix_contacttype_ak_contacttype_name
ON adventureworks_person.contacttype
USING BTREE (name ASC);