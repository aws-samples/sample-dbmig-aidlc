-- Person.BusinessEntityAddress -> person.businessentityaddress
CREATE TABLE person.businessentityaddress (
    businessentityid integer NOT NULL,
    addressid        integer NOT NULL,
    addresstypeid    integer NOT NULL,
    rowguid          uuid NOT NULL DEFAULT gen_random_uuid(),
    modifieddate     timestamp NOT NULL DEFAULT now(),
    CONSTRAINT pk_businessentityaddress PRIMARY KEY (businessentityid, addressid, addresstypeid)
);
CREATE UNIQUE INDEX ak_bea_rowguid ON person.businessentityaddress (rowguid);
CREATE INDEX ix_bea_addressid ON person.businessentityaddress (addressid);
CREATE INDEX ix_bea_addresstypeid ON person.businessentityaddress (addresstypeid);
ALTER TABLE person.businessentityaddress ADD CONSTRAINT fk_bea_address FOREIGN KEY (addressid) REFERENCES person.address (addressid);
ALTER TABLE person.businessentityaddress ADD CONSTRAINT fk_bea_addresstype FOREIGN KEY (addresstypeid) REFERENCES person.addresstype (addresstypeid);
ALTER TABLE person.businessentityaddress ADD CONSTRAINT fk_bea_businessentity FOREIGN KEY (businessentityid) REFERENCES person.businessentity (businessentityid);
