ALTER TABLE adventureworks_person.businessentityaddress
ADD CONSTRAINT fk_businessentityaddress_address_addressid_699149536 FOREIGN KEY (addressid) 
REFERENCES adventureworks_person.address (addressid)
ON UPDATE NO ACTION
ON DELETE NO ACTION;