CREATE TABLE person.countryregion(
    countryregioncode VARCHAR(3) NOT NULL,
    name dbo.name NOT NULL,
    modifieddate TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT (clock_timestamp())
)
        WITH (
        OIDS=FALSE
        );