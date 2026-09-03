ALTER TABLE person.businessentityaddress
ADD CONSTRAINT fk_businessentityaddress_addresstype_addresstypeid_715149593 FOREIGN KEY (addresstypeid) 
REFERENCES person.addresstype (addresstypeid)
ON UPDATE NO ACTION
ON DELETE NO ACTION;