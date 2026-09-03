CREATE UNIQUE INDEX ix_stateprovince_ak_stateprovince_stateprovincecode_co$d0a43de1
ON person.stateprovince
USING BTREE (stateprovincecode ASC, countryregioncode ASC);