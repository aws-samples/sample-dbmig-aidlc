-- HumanResources.Employee -> humanresources.employee
-- hierarchyid OrganizationNode -> text (path string, e.g. '/1/1/'); custom-loaded via OrganizationNode.ToString().
-- OrganizationLevel (computed AS OrganizationNode.GetLevel()) -> plain smallint, loaded from the source value.
-- money n/a here. bit -> boolean. nchar(1) -> char(1). uniqueidentifier -> uuid.
-- CK_Employee_BirthDate / CK_Employee_HireDate used getdate() (non-deterministic) -> PG CHECK must be IMMUTABLE,
--   so only the static lower bounds are kept; the "<= today" upper bounds are dropped (flagged).
-- INSTEAD OF DELETE trigger (tables can't have INSTEAD OF in PG) -> BEFORE DELETE trigger raising an exception.
CREATE TABLE humanresources.employee (
    businessentityid integer NOT NULL,
    nationalidnumber varchar(15) NOT NULL,
    loginid          varchar(256) NOT NULL,
    organizationnode text,
    organizationlevel smallint,
    jobtitle         varchar(50) NOT NULL,
    birthdate        date NOT NULL,
    maritalstatus    char(1) NOT NULL,
    gender           char(1) NOT NULL,
    hiredate         date NOT NULL,
    salariedflag     boolean NOT NULL DEFAULT true,
    vacationhours    smallint NOT NULL DEFAULT 0,
    sickleavehours   smallint NOT NULL DEFAULT 0,
    currentflag      boolean NOT NULL DEFAULT true,
    rowguid          uuid NOT NULL DEFAULT gen_random_uuid(),
    modifieddate     timestamp NOT NULL DEFAULT now(),
    CONSTRAINT pk_employee PRIMARY KEY (businessentityid),
    CONSTRAINT ck_employee_birthdate CHECK (birthdate >= DATE '1930-01-01'),
    CONSTRAINT ck_employee_maritalstatus CHECK (upper(maritalstatus) IN ('S','M')),
    CONSTRAINT ck_employee_hiredate CHECK (hiredate >= DATE '1996-07-01'),
    CONSTRAINT ck_employee_gender CHECK (upper(gender) IN ('F','M')),
    CONSTRAINT ck_employee_vacationhours CHECK (vacationhours >= -40 AND vacationhours <= 240),
    CONSTRAINT ck_employee_sickleavehours CHECK (sickleavehours >= 0 AND sickleavehours <= 120)
);
CREATE UNIQUE INDEX ak_employee_loginid ON humanresources.employee (loginid);
CREATE UNIQUE INDEX ak_employee_nationalidnumber ON humanresources.employee (nationalidnumber);
CREATE UNIQUE INDEX ak_employee_rowguid ON humanresources.employee (rowguid);
CREATE INDEX ix_employee_orglevel_orgnode ON humanresources.employee (organizationlevel, organizationnode);
CREATE INDEX ix_employee_orgnode ON humanresources.employee (organizationnode);
ALTER TABLE humanresources.employee ADD CONSTRAINT fk_employee_person
    FOREIGN KEY (businessentityid) REFERENCES person.person (businessentityid);

-- dEmployee: block deletes (SQL Server INSTEAD OF DELETE). Function pre-data; trigger deferred to post-data.
CREATE OR REPLACE FUNCTION humanresources.employee_prevent_delete() RETURNS trigger AS $$
BEGIN
  RAISE EXCEPTION 'Employees cannot be deleted. They can only be marked as not current.';
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER demployee
  BEFORE DELETE ON humanresources.employee
  FOR EACH ROW EXECUTE FUNCTION humanresources.employee_prevent_delete();
