CREATE OR REPLACE FUNCTION adventureworks_dbo.ufngetproductlistprice(IN par_productid INTEGER, IN par_orderdate TIMESTAMP WITHOUT TIME ZONE)
RETURNS NUMERIC
AS
$BODY$
DECLARE
    var_ListPrice NUMERIC(19, 4);
BEGIN
    SELECT
        plph.listprice
        INTO var_ListPrice
        FROM adventureworks_production.product AS p
        INNER JOIN adventureworks_production.productlistpricehistory AS plph
            ON p.productid = plph.productid AND p.productid = par_ProductID AND par_OrderDate BETWEEN plph.startdate AND COALESCE(plph.enddate, aws_sqlserver_ext.conv_string_to_datetime('DATETIME', '99991231', 112));
    /* Make sure we get all the prices! */
    RETURN var_ListPrice;
END;
$BODY$
LANGUAGE  plpgsql;