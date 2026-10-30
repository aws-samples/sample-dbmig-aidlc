CREATE TABLE adventureworks_dbo.databaselog(
    databaselogid INTEGER NOT NULL GENERATED ALWAYS AS IDENTITY,
    posttime TIMESTAMP WITHOUT TIME ZONE NOT NULL,
    databaseuser VARCHAR(128) NOT NULL,
    event VARCHAR(128) NOT NULL,
    schema VARCHAR(128),
    object VARCHAR(128),
    tsql TEXT NOT NULL,
    xmlevent XML NOT NULL
)
        WITH (
        OIDS=FALSE
        );