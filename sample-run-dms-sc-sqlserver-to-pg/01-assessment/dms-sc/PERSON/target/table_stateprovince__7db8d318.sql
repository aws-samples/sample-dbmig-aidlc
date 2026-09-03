CREATE TABLE person.stateprovince(
    stateprovinceid INTEGER NOT NULL GENERATED ALWAYS AS IDENTITY,
    stateprovincecode CHAR(3) NOT NULL,
    countryregioncode VARCHAR(3) NOT NULL,
    isonlystateprovinceflag dbo.flag NOT NULL DEFAULT (1),
    name dbo.name NOT NULL,
    territoryid INTEGER NOT NULL,
    rowguid UUID NOT NULL DEFAULT (uuid_generate_v4()),
    modifieddate TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT (clock_timestamp())
)
        WITH (
        OIDS=FALSE
        );