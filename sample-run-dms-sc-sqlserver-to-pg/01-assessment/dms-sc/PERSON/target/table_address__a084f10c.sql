CREATE TABLE person.address(
    addressid INTEGER NOT NULL GENERATED ALWAYS AS IDENTITY,
    addressline1 VARCHAR(60) NOT NULL,
    addressline2 VARCHAR(60),
    city VARCHAR(30) NOT NULL,
    stateprovinceid INTEGER NOT NULL,
    postalcode VARCHAR(15) NOT NULL,
    spatiallocation GEOGRAPHY,
    rowguid UUID NOT NULL DEFAULT (uuid_generate_v4()),
    modifieddate TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT (clock_timestamp())
)
        WITH (
        OIDS=FALSE
        );