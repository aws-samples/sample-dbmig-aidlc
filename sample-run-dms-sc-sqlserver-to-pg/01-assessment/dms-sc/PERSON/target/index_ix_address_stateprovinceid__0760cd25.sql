CREATE INDEX ix_address_ix_address_stateprovinceid
ON person.address
USING BTREE (stateprovinceid ASC);