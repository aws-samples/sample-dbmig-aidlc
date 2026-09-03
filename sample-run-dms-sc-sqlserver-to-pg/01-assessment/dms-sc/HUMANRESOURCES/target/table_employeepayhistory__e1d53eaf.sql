CREATE TABLE humanresources.employeepayhistory(
    businessentityid INTEGER NOT NULL,
    ratechangedate TIMESTAMP WITHOUT TIME ZONE NOT NULL,
    rate NUMERIC(19,4) NOT NULL,
    payfrequency SMALLINT NOT NULL,
    modifieddate TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT (clock_timestamp())
)
        WITH (
        OIDS=FALSE
        );