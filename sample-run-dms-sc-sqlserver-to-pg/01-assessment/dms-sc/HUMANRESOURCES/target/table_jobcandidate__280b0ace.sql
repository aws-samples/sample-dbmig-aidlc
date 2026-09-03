CREATE TABLE humanresources.jobcandidate(
    jobcandidateid INTEGER NOT NULL GENERATED ALWAYS AS IDENTITY,
    businessentityid INTEGER,
    resume XML,
    modifieddate TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT (clock_timestamp())
)
        WITH (
        OIDS=FALSE
        );