CREATE UNIQUE INDEX ix_stateprovince_ak_stateprovince_name
ON person.stateprovince
USING BTREE (name ASC);