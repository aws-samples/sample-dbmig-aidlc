CREATE TABLE person.phonenumbertype(
    phonenumbertypeid INTEGER NOT NULL GENERATED ALWAYS AS IDENTITY,
    name dbo.name NOT NULL,
    modifieddate TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT (clock_timestamp())
)
        WITH (
        OIDS=FALSE
        );