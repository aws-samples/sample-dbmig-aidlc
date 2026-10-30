ALTER TABLE adventureworks_person.stateprovince
ADD CONSTRAINT fk_stateprovince_salesterritory_territoryid_1931153925 FOREIGN KEY (territoryid) 
REFERENCES adventureworks_sales.salesterritory (territoryid)
ON UPDATE NO ACTION
ON DELETE NO ACTION;