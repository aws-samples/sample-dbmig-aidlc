-- Person.PersonPhone -> person.personphone
CREATE TABLE person.personphone (
    businessentityid  integer NOT NULL,
    phonenumber       varchar(25) NOT NULL,
    phonenumbertypeid integer NOT NULL,
    modifieddate      timestamp NOT NULL DEFAULT now(),
    CONSTRAINT pk_personphone PRIMARY KEY (businessentityid, phonenumber, phonenumbertypeid)
);
CREATE INDEX ix_personphone_phonenumber ON person.personphone (phonenumber);
ALTER TABLE person.personphone ADD CONSTRAINT fk_personphone_phonenumbertype FOREIGN KEY (phonenumbertypeid) REFERENCES person.phonenumbertype (phonenumbertypeid);
ALTER TABLE person.personphone ADD CONSTRAINT fk_personphone_person FOREIGN KEY (businessentityid) REFERENCES person.person (businessentityid);
