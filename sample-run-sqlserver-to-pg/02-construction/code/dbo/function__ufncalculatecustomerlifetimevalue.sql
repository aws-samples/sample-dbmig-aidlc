-- DECIMAL(10,2) locals: every assignment rounds to 2 dp, as in SQL Server.
-- DATEDIFF(DAY, d, GETDATE()) counts day boundaries = current_date - d::date.
CREATE OR REPLACE FUNCTION dbo.ufncalculatecustomerlifetimevalue(p_customerid integer)
RETURNS numeric(10,2) LANGUAGE plpgsql STABLE AS $$
DECLARE
    v_totalspent numeric(10,2);
    v_firstorderdate date;
    v_days integer;
    v_lifetimevalue numeric(10,2);
BEGIN
    SELECT sum(totalamount), min(orderdate)::date INTO v_totalspent, v_firstorderdate
    FROM dbo.shopping
    WHERE customerid = p_customerid AND trim(status) <> 'Refund Requested';
    v_days := current_date - v_firstorderdate;
    IF v_days = 0 THEN
        v_lifetimevalue := v_totalspent;
    ELSE
        v_lifetimevalue := (v_totalspent / v_days) * 365.25;
    END IF;
    RETURN v_lifetimevalue;
END $$;
