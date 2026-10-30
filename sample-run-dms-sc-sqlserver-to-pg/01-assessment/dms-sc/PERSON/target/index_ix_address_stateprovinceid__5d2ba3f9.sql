CREATE INDEX ix_address_ix_address_stateprovinceid
ON adventureworks_person.address
USING BTREE (stateprovinceid ASC);