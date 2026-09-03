CREATE TABLE person.person(
    businessentityid INTEGER NOT NULL,
    persontype CHAR(2) NOT NULL,
    namestyle dbo.namestyle NOT NULL DEFAULT (0),
    title VARCHAR(8),
    firstname dbo.name NOT NULL,
    middlename dbo.name,
    lastname dbo.name NOT NULL,
    suffix VARCHAR(10),
    emailpromotion INTEGER NOT NULL DEFAULT (0),
    additionalcontactinfo XML,
    demographics XML,
    rowguid UUID NOT NULL DEFAULT (uuid_generate_v4()),
    modifieddate TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT (clock_timestamp())
)
        WITH (
        OIDS=FALSE
        );