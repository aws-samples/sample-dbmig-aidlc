CREATE TABLE adventureworks_person.personphone(
    businessentityid INTEGER NOT NULL,
    phonenumber adventureworks_dbo.phone NOT NULL,
    phonenumbertypeid INTEGER NOT NULL,
    modifieddate TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT (clock_timestamp())
)
        WITH (
        OIDS=FALSE
        );