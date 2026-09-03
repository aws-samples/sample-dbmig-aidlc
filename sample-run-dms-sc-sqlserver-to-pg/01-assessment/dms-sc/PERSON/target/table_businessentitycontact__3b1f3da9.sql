CREATE TABLE person.businessentitycontact(
    businessentityid INTEGER NOT NULL,
    personid INTEGER NOT NULL,
    contacttypeid INTEGER NOT NULL,
    rowguid UUID NOT NULL DEFAULT (uuid_generate_v4()),
    modifieddate TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT (clock_timestamp())
)
        WITH (
        OIDS=FALSE
        );