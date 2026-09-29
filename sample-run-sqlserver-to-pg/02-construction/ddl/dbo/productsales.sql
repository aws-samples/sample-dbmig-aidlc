-- No primary key in the source.
CREATE TABLE dbo.productsales (
  saleid numeric(18,0) NOT NULL, productid integer NOT NULL, saledate date NOT NULL,
  quantity numeric(10,0) NOT NULL, unitprice numeric(9,2) NOT NULL, totalamount numeric(11,2) NOT NULL,
  customerid integer NOT NULL, saleprice numeric(9,2), regionid numeric(10,0)
);
