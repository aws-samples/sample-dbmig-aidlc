CREATE OR REPLACE FUNCTION adventureworks_dbo.ufngetpurchaseorderstatustext(IN par_status SMALLINT)
RETURNS VARCHAR
AS
$BODY$
/* Returns the sales order status text representation for the status value. */
DECLARE
    var_ret VARCHAR(15);
BEGIN
    var_ret :=
    CASE par_Status
        WHEN 1 THEN 'Pending'
        WHEN 2 THEN 'Approved'
        WHEN 3 THEN 'Rejected'
        WHEN 4 THEN 'Complete'
        ELSE '** Invalid **'
    END;
    RETURN var_ret;
END;
$BODY$
LANGUAGE  plpgsql;