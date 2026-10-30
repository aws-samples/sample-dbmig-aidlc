CREATE UNIQUE INDEX ix_countryregion_ak_countryregion_name
ON adventureworks_person.countryregion
USING BTREE (name ASC);