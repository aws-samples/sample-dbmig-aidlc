-- Result-set procedure -> set-returning FUNCTION.
-- @Amount NUMERIC defaults to numeric(18,0) in SQL Server: the argument is ROUNDED to an integer
-- on the way in — reproduced with round(). '|' + NULL + '|' is NULL in both engines.
CREATE OR REPLACE FUNCTION dbo.uspshoppinglevelamount(p_percent integer, p_amount numeric)
RETURNS TABLE (orderid integer, amountlevel text)
LANGUAGE sql STABLE AS $$
    SELECT s.orderid,
           '|' || CASE WHEN p_percent > 100 THEN
                        CASE WHEN s.totalamount > round(p_amount) THEN 'more than' ELSE 'less than' END
                  END || '|'
    FROM dbo.shopping s
$$;
