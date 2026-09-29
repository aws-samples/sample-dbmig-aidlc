-- No primary key in the source (none invented).
CREATE TABLE dbo.person (
  businessentityid integer NOT NULL, persontype char(2) NOT NULL,
  namestyle boolean NOT NULL DEFAULT false,      -- dbo.NameStyle (bit)
  title varchar(8), firstname varchar(100) NOT NULL, middlename varchar(100), lastname varchar(100) NOT NULL,
  suffix varchar(10), emailpromotion integer NOT NULL DEFAULT 0,
  additionalcontactinfo xml, demographics xml,
  rowguid uuid NOT NULL DEFAULT gen_random_uuid(),   -- uniqueidentifier / newid()
  modifieddate timestamp(3) NOT NULL DEFAULT localtimestamp
);
CREATE UNIQUE INDEX ak_person_rowguid ON dbo.person (rowguid);
CREATE INDEX ix_person_lastname_firstname_middlename ON dbo.person (lastname, firstname, middlename);
