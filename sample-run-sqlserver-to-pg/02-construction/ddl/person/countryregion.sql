-- Person.CountryRegion -> person.countryregion
CREATE TABLE person.countryregion (
    countryregioncode varchar(3) NOT NULL,
    name              varchar(50) NOT NULL,
    modifieddate      timestamp NOT NULL DEFAULT now(),
    CONSTRAINT pk_countryregion PRIMARY KEY (countryregioncode)
);
CREATE UNIQUE INDEX ak_countryregion_name ON person.countryregion (name);
