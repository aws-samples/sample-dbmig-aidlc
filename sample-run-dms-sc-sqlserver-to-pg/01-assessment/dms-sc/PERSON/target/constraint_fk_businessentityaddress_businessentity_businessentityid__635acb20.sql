ALTER TABLE person.businessentityaddress
ADD CONSTRAINT fk_businessentityaddress_businessentity_businessentityid_731149650 FOREIGN KEY (businessentityid) 
REFERENCES person.businessentity (businessentityid)
ON UPDATE NO ACTION
ON DELETE NO ACTION;