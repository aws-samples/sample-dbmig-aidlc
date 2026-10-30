CREATE TABLE adventureworks_humanresources.department(
    departmentid SMALLINT NOT NULL GENERATED ALWAYS AS IDENTITY,
    name adventureworks_dbo.name NOT NULL,
    groupname adventureworks_dbo.name NOT NULL,
    modifieddate TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT (clock_timestamp())
)
        WITH (
        OIDS=FALSE
        );