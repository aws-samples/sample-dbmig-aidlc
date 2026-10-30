ALTER TABLE adventureworks_person.address
ADD CONSTRAINT fk_address_stateprovince_stateprovinceid_635149308 FOREIGN KEY (stateprovinceid) 
REFERENCES adventureworks_person.stateprovince (stateprovinceid)
ON UPDATE NO ACTION
ON DELETE NO ACTION;