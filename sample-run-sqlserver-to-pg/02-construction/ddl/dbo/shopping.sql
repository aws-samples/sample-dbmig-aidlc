CREATE TABLE dbo.shopping (
  orderid integer PRIMARY KEY, customerid integer, orderdate timestamp(3),
  totalamount numeric(10,2), status varchar(20)
);
