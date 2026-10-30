CREATE TABLE adventureworks_person.phonenumbertype(
    phonenumbertypeid INTEGER NOT NULL GENERATED ALWAYS AS IDENTITY,
    name adventureworks_dbo.name NOT NULL,
    modifieddate TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT (clock_timestamp())
)
        WITH (
        OIDS=FALSE
        );