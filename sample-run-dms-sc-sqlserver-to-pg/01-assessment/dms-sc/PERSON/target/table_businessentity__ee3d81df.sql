CREATE TABLE person.businessentity(
    businessentityid INTEGER NOT NULL GENERATED ALWAYS AS IDENTITY,
    rowguid UUID NOT NULL DEFAULT (uuid_generate_v4()),
    modifieddate TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT (clock_timestamp())
)
        WITH (
        OIDS=FALSE
        );