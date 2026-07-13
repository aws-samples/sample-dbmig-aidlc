-- Person.BusinessEntityContact -> person.businessentitycontact
CREATE TABLE person.businessentitycontact (
    businessentityid integer NOT NULL,
    personid         integer NOT NULL,
    contacttypeid    integer NOT NULL,
    rowguid          uuid NOT NULL DEFAULT gen_random_uuid(),
    modifieddate     timestamp NOT NULL DEFAULT now(),
    CONSTRAINT pk_businessentitycontact PRIMARY KEY (businessentityid, personid, contacttypeid)
);
CREATE UNIQUE INDEX ak_bec_rowguid ON person.businessentitycontact (rowguid);
CREATE INDEX ix_bec_contacttypeid ON person.businessentitycontact (contacttypeid);
CREATE INDEX ix_bec_personid ON person.businessentitycontact (personid);
ALTER TABLE person.businessentitycontact ADD CONSTRAINT fk_bec_businessentity FOREIGN KEY (businessentityid) REFERENCES person.businessentity (businessentityid);
ALTER TABLE person.businessentitycontact ADD CONSTRAINT fk_bec_contacttype FOREIGN KEY (contacttypeid) REFERENCES person.contacttype (contacttypeid);
ALTER TABLE person.businessentitycontact ADD CONSTRAINT fk_bec_person FOREIGN KEY (personid) REFERENCES person.person (businessentityid);
