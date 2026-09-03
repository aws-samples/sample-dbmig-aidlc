ALTER TABLE person.businessentityaddress
ADD CONSTRAINT fk_businessentityaddress_address_addressid_699149536 FOREIGN KEY (addressid) 
REFERENCES person.address (addressid)
ON UPDATE NO ACTION
ON DELETE NO ACTION;