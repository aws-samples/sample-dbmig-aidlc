CREATE OR REPLACE FUNCTION adventureworks_dbo.ufngetproductstandardcost(IN par_productid INTEGER, IN par_orderdate TIMESTAMP WITHOUT TIME ZONE)
RETURNS NUMERIC
AS
$BODY$
/* Returns the standard cost for the product on a specific date. */
DECLARE
    var_StandardCost NUMERIC(19, 4);
BEGIN
    SELECT
        pch.standardcost
        INTO var_StandardCost
        FROM adventureworks_production.product AS p
        INNER JOIN adventureworks_production.productcosthistory AS pch
            ON p.productid = pch.productid AND p.productid = par_ProductID AND par_OrderDate BETWEEN pch.startdate AND COALESCE(pch.enddate, aws_sqlserver_ext.conv_string_to_datetime('DATETIME', '99991231', 112));
    /* Make sure we get all the prices! */
    RETURN var_StandardCost;
END;
$BODY$
LANGUAGE  plpgsql;