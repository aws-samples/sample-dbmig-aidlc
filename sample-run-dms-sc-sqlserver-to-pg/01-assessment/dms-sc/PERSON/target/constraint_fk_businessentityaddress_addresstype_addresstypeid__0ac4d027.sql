ALTER TABLE adventureworks_person.businessentityaddress
ADD CONSTRAINT fk_businessentityaddress_addresstype_addresstypeid_715149593 FOREIGN KEY (addresstypeid) 
REFERENCES adventureworks_person.addresstype (addresstypeid)
ON UPDATE NO ACTION
ON DELETE NO ACTION;