CREATE TABLE adventureworks_dbo.awbuildversion(
    systeminformationid SMALLINT NOT NULL GENERATED ALWAYS AS IDENTITY,
    "Database Version" VARCHAR(25) NOT NULL,
    versiondate TIMESTAMP WITHOUT TIME ZONE NOT NULL,
    modifieddate TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT (clock_timestamp())
)
        WITH (
        OIDS=FALSE
        );