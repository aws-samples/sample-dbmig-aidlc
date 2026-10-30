CREATE UNIQUE INDEX ix_stateprovince_ak_stateprovince_rowguid
ON adventureworks_person.stateprovince
USING BTREE (rowguid ASC);