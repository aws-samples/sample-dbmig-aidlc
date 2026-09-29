CREATE TABLE dbo.members (
  customerid integer PRIMARY KEY,
  firstname varchar(50), lastname varchar(50), email varchar(100), phone varchar(20),
  registrationdate date, totalordersum numeric(10,2)
);
