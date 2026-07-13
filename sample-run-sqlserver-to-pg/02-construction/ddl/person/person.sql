-- Person.Person -> person.person
-- nchar->char, bit->boolean, uniqueidentifier->uuid, xml->xml. CHECK constraints preserved.
-- The SQL Server AFTER trigger iuPerson (defaults the Demographics survey XML) is converted to a
-- PL/pgSQL BEFORE trigger. The original also injects a <TotalPurchaseYTD> node into an existing
-- Demographics doc that lacks it (via XML .modify()); that branch is simplified to the NULL-default
-- case here (the common path) and flagged.
CREATE TABLE person.person (
    businessentityid      integer NOT NULL,
    persontype            char(2) NOT NULL,
    namestyle             boolean NOT NULL DEFAULT false,
    title                 varchar(8),
    firstname             varchar(50) NOT NULL,
    middlename            varchar(50),
    lastname              varchar(50) NOT NULL,
    suffix                varchar(10),
    emailpromotion        integer NOT NULL DEFAULT 0,
    additionalcontactinfo xml,
    demographics          xml,
    rowguid               uuid NOT NULL DEFAULT gen_random_uuid(),
    modifieddate          timestamp NOT NULL DEFAULT now(),
    CONSTRAINT pk_person PRIMARY KEY (businessentityid),
    CONSTRAINT ck_person_emailpromotion CHECK (emailpromotion >= 0 AND emailpromotion <= 2),
    CONSTRAINT ck_person_persontype CHECK (persontype IS NULL OR upper(persontype) IN ('GC','SP','EM','IN','VC','SC'))
);
CREATE UNIQUE INDEX ak_person_rowguid ON person.person (rowguid);
CREATE INDEX ix_person_lastname_firstname_middlename ON person.person (lastname, firstname, middlename);
ALTER TABLE person.person ADD CONSTRAINT fk_person_businessentity
    FOREIGN KEY (businessentityid) REFERENCES person.businessentity (businessentityid);

-- iuPerson trigger (default Demographics survey XML). Function is pre-data; trigger deferred to post-data.
CREATE OR REPLACE FUNCTION person.person_default_demographics() RETURNS trigger AS $$
BEGIN
  IF NEW.demographics IS NULL THEN
    NEW.demographics := xmlparse(document
      '<IndividualSurvey xmlns="http://schemas.microsoft.com/sqlserver/2004/07/adventure-works/IndividualSurvey"><TotalPurchaseYTD>0.00</TotalPurchaseYTD></IndividualSurvey>');
  END IF;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER iuperson
  BEFORE INSERT OR UPDATE ON person.person
  FOR EACH ROW EXECUTE FUNCTION person.person_default_demographics();
