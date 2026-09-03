CREATE TABLE person.emailaddress(
    businessentityid INTEGER NOT NULL,
    emailaddressid INTEGER NOT NULL GENERATED ALWAYS AS IDENTITY,
    emailaddress VARCHAR(50),
    rowguid UUID NOT NULL DEFAULT (uuid_generate_v4()),
    modifieddate TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT (clock_timestamp())
)
        WITH (
        OIDS=FALSE
        );