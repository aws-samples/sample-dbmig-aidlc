CREATE TABLE person.password(
    businessentityid INTEGER NOT NULL,
    passwordhash VARCHAR(128) NOT NULL,
    passwordsalt VARCHAR(10) NOT NULL,
    rowguid UUID NOT NULL DEFAULT (uuid_generate_v4()),
    modifieddate TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT (clock_timestamp())
)
        WITH (
        OIDS=FALSE
        );