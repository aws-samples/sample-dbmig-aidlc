CREATE OR REPLACE FUNCTION adventureworks_dbo.ufngetstock(IN par_productid INTEGER)
RETURNS INTEGER
AS
$BODY$
/* Returns the stock level for the product. This function is used internally only */
DECLARE
    var_ret INTEGER;
BEGIN
    SELECT
        SUM(p.quantity)
        INTO var_ret
        FROM adventureworks_production.productinventory AS p
        WHERE p.productid = par_ProductID AND p.locationid = '6';
    /* Only look at inventory in the misc storage */

    IF (var_ret IS NULL) THEN
        var_ret := 0;
    END IF;
    RETURN var_ret;
END;
$BODY$
LANGUAGE  plpgsql;