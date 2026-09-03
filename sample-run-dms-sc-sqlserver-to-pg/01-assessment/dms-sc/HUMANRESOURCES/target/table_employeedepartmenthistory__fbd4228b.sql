CREATE TABLE humanresources.employeedepartmenthistory(
    businessentityid INTEGER NOT NULL,
    departmentid SMALLINT NOT NULL,
    shiftid SMALLINT NOT NULL,
    startdate DATE NOT NULL,
    enddate DATE,
    modifieddate TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT (clock_timestamp())
)
        WITH (
        OIDS=FALSE
        );