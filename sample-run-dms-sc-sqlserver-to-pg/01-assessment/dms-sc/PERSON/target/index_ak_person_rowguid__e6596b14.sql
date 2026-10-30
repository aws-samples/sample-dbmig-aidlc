CREATE UNIQUE INDEX ix_person_ak_person_rowguid
ON adventureworks_person.person
USING BTREE (rowguid ASC);