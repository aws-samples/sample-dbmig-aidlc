-- HumanResources.EmployeeDepartmentHistory -> humanresources.employeedepartmenthistory
-- tinyint ShiftID -> smallint. FKs deferred to post-data.
CREATE TABLE humanresources.employeedepartmenthistory (
    businessentityid integer NOT NULL,
    departmentid     smallint NOT NULL,
    shiftid          smallint NOT NULL,
    startdate        date NOT NULL,
    enddate          date,
    modifieddate     timestamp NOT NULL DEFAULT now(),
    CONSTRAINT pk_employeedepartmenthistory PRIMARY KEY (businessentityid, startdate, departmentid, shiftid),
    CONSTRAINT ck_edh_enddate CHECK (enddate >= startdate OR enddate IS NULL)
);
CREATE INDEX ix_edh_departmentid ON humanresources.employeedepartmenthistory (departmentid);
CREATE INDEX ix_edh_shiftid ON humanresources.employeedepartmenthistory (shiftid);
ALTER TABLE humanresources.employeedepartmenthistory ADD CONSTRAINT fk_edh_shift FOREIGN KEY (shiftid) REFERENCES humanresources.shift (shiftid);
ALTER TABLE humanresources.employeedepartmenthistory ADD CONSTRAINT fk_edh_department FOREIGN KEY (departmentid) REFERENCES humanresources.department (departmentid);
ALTER TABLE humanresources.employeedepartmenthistory ADD CONSTRAINT fk_edh_employee FOREIGN KEY (businessentityid) REFERENCES humanresources.employee (businessentityid);
