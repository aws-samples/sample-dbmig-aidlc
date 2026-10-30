ALTER TABLE adventureworks_person.stateprovince
ADD CONSTRAINT fk_stateprovince_countryregion_countryregioncode_1915153868 FOREIGN KEY (countryregioncode) 
REFERENCES adventureworks_person.countryregion (countryregioncode)
ON UPDATE NO ACTION
ON DELETE NO ACTION;