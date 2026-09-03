CREATE TABLE person.personphone(
    businessentityid INTEGER NOT NULL,
    phonenumber dbo.phone NOT NULL,
    phonenumbertypeid INTEGER NOT NULL,
    modifieddate TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT (clock_timestamp())
)
        WITH (
        OIDS=FALSE
        );