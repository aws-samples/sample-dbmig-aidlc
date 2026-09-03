CREATE TABLE humanresources.shift(
    shiftid SMALLINT NOT NULL GENERATED ALWAYS AS IDENTITY,
    name dbo.name NOT NULL,
    starttime TIME(6) WITHOUT TIME ZONE NOT NULL,
    endtime TIME(6) WITHOUT TIME ZONE NOT NULL,
    modifieddate TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT (clock_timestamp())
)
        WITH (
        OIDS=FALSE
        );