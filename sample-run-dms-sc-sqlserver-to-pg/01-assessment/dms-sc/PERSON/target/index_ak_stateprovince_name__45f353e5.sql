CREATE UNIQUE INDEX ix_stateprovince_ak_stateprovince_name
ON adventureworks_person.stateprovince
USING BTREE (name ASC);