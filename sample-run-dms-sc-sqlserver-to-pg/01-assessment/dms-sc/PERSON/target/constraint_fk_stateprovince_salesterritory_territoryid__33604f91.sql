ALTER TABLE person.stateprovince
ADD CONSTRAINT fk_stateprovince_salesterritory_territoryid_1931153925 FOREIGN KEY (territoryid) 
REFERENCES sales.salesterritory (territoryid)
ON UPDATE NO ACTION
ON DELETE NO ACTION;