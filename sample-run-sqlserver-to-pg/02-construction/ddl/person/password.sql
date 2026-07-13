-- Person.Password -> person.password
CREATE TABLE person.password (
    businessentityid integer NOT NULL,
    passwordhash     varchar(128) NOT NULL,
    passwordsalt     varchar(10) NOT NULL,
    rowguid          uuid NOT NULL DEFAULT gen_random_uuid(),
    modifieddate     timestamp NOT NULL DEFAULT now(),
    CONSTRAINT pk_password PRIMARY KEY (businessentityid)
);
ALTER TABLE person.password ADD CONSTRAINT fk_password_person
    FOREIGN KEY (businessentityid) REFERENCES person.person (businessentityid);
