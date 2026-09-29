CREATE TABLE dbo.coupons (
  ticketid integer PRIMARY KEY,       -- system-named PK__Coupons__… replaced by the default name
  customerid integer, orderid integer, issuedescription text,
  createddate timestamp(3), resolveddate timestamp(3), status varchar(20), osuser varchar(10)
);
