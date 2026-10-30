CREATE TABLE adventureworks_dbo.errorlog(
    errorlogid INTEGER NOT NULL GENERATED ALWAYS AS IDENTITY,
    errortime TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT (clock_timestamp()),
    username VARCHAR(128) NOT NULL,
    errornumber INTEGER NOT NULL,
    errorseverity INTEGER,
    errorstate INTEGER,
    errorprocedure VARCHAR(126),
    errorline INTEGER,
    errormessage VARCHAR(4000) NOT NULL
)
        WITH (
        OIDS=FALSE
        );