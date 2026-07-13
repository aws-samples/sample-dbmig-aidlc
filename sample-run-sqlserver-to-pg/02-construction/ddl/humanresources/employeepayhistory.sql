-- HumanResources.EmployeePayHistory -> humanresources.employeepayhistory
-- money Rate -> numeric(19,4); tinyint PayFrequency -> smallint; datetime -> timestamp.
CREATE TABLE humanresources.employeepayhistory (
    businessentityid integer NOT NULL,
    ratechangedate   timestamp NOT NULL,
    rate             numeric(19,4) NOT NULL,
    payfrequency     smallint NOT NULL,
    modifieddate     timestamp NOT NULL DEFAULT now(),
    CONSTRAINT pk_employeepayhistory PRIMARY KEY (businessentityid, ratechangedate),
    CONSTRAINT ck_eph_payfrequency CHECK (payfrequency IN (1, 2)),
    CONSTRAINT ck_eph_rate CHECK (rate >= 6.50 AND rate <= 200.00)
);
ALTER TABLE humanresources.employeepayhistory ADD CONSTRAINT fk_eph_employee
    FOREIGN KEY (businessentityid) REFERENCES humanresources.employee (businessentityid);
