CREATE TABLE humanresources.employee(
    businessentityid INTEGER NOT NULL,
    nationalidnumber VARCHAR(15) NOT NULL,
    loginid VARCHAR(256) NOT NULL,
    organizationnode VARCHAR(8000),
    organizationlevel SMALLINT,
    jobtitle VARCHAR(50) NOT NULL,
    birthdate DATE NOT NULL,
    maritalstatus CHAR(1) NOT NULL,
    gender CHAR(1) NOT NULL,
    hiredate DATE NOT NULL,
    salariedflag dbo.flag NOT NULL DEFAULT (1),
    vacationhours SMALLINT NOT NULL DEFAULT (0),
    sickleavehours SMALLINT NOT NULL DEFAULT (0),
    currentflag dbo.flag NOT NULL DEFAULT (1),
    rowguid UUID NOT NULL DEFAULT (uuid_generate_v4()),
    modifieddate TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT (clock_timestamp())
)
        WITH (
        OIDS=FALSE
        );