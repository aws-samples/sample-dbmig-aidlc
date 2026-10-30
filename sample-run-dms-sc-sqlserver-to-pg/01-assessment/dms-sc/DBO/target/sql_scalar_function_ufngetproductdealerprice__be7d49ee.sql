CREATE OR REPLACE FUNCTION adventureworks_dbo.ufngetproductdealerprice(IN par_productid INTEGER, IN par_orderdate TIMESTAMP WITHOUT TIME ZONE)
RETURNS NUMERIC
AS
$BODY$
/* Returns the dealer price for the product on a specific date. */
DECLARE
    var_DealerPrice NUMERIC(19, 4);
    var_DealerDiscount NUMERIC(19, 4);
BEGIN
    var_DealerDiscount := 0.60;
    /* 60% of list price */
    SELECT
        plph.listprice * var_DealerDiscount
        INTO var_DealerPrice
        FROM adventureworks_production.product AS p
        INNER JOIN adventureworks_production.productlistpricehistory AS plph
            ON p.productid = plph.productid AND p.productid = par_ProductID AND par_OrderDate BETWEEN plph.startdate AND COALESCE(plph.enddate, aws_sqlserver_ext.conv_string_to_datetime('DATETIME', '99991231', 112));
    /* Make sure we get all the prices! */
    RETURN var_DealerPrice;
END;
$BODY$
LANGUAGE  plpgsql;