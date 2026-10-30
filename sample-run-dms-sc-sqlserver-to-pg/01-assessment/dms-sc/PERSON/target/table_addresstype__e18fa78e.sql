CREATE TABLE adventureworks_person.addresstype(
    addresstypeid INTEGER NOT NULL GENERATED ALWAYS AS IDENTITY,
    name adventureworks_dbo.name NOT NULL,
    rowguid UUID NOT NULL DEFAULT (uuid_generate_v4()),
    modifieddate TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT (clock_timestamp())
)
        WITH (
        OIDS=FALSE
        );