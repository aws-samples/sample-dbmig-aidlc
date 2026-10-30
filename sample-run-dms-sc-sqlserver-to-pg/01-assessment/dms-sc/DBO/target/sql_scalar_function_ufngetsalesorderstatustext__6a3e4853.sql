CREATE OR REPLACE FUNCTION adventureworks_dbo.ufngetsalesorderstatustext(IN par_status SMALLINT)
RETURNS VARCHAR
AS
$BODY$
/* Returns the sales order status text representation for the status value. */
DECLARE
    var_ret VARCHAR(15);
BEGIN
    var_ret :=
    CASE par_Status
        WHEN 1 THEN 'In process'
        WHEN 2 THEN 'Approved'
        WHEN 3 THEN 'Backordered'
        WHEN 4 THEN 'Rejected'
        WHEN 5 THEN 'Shipped'
        WHEN 6 THEN 'Cancelled'
        ELSE '** Invalid **'
    END;
    RETURN var_ret;
END;
$BODY$
LANGUAGE  plpgsql;