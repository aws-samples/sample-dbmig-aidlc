ALTER TABLE person.stateprovince
ADD CONSTRAINT fk_stateprovince_countryregion_countryregioncode_1915153868 FOREIGN KEY (countryregioncode) 
REFERENCES person.countryregion (countryregioncode)
ON UPDATE NO ACTION
ON DELETE NO ACTION;