CREATE UNIQUE INDEX ix_address_ix_address_addressline1_addressline2_city_s$63444a04
ON person.address
USING BTREE (addressline1 ASC, addressline2 ASC, city ASC, stateprovinceid ASC, postalcode ASC);