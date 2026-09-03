CREATE TABLE person.businessentityaddress(
    businessentityid INTEGER NOT NULL,
    addressid INTEGER NOT NULL,
    addresstypeid INTEGER NOT NULL,
    rowguid UUID NOT NULL DEFAULT (uuid_generate_v4()),
    modifieddate TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT (clock_timestamp())
)
        WITH (
        OIDS=FALSE
        );