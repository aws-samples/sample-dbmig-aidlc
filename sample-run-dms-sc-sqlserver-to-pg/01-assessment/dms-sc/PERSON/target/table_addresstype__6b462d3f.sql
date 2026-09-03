CREATE TABLE person.addresstype(
    addresstypeid INTEGER NOT NULL GENERATED ALWAYS AS IDENTITY,
    name dbo.name NOT NULL,
    rowguid UUID NOT NULL DEFAULT (uuid_generate_v4()),
    modifieddate TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT (clock_timestamp())
)
        WITH (
        OIDS=FALSE
        );