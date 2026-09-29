-- tinyint (0-255) -> integer parameter: a smallint parameter does not resolve for callers passing an
-- integer literal (PostgreSQL will not implicitly narrow integer -> smallint in function lookup).
CREATE OR REPLACE FUNCTION dbo.ufngetpurchaseorderstatustext(p_status integer)
RETURNS varchar(15) LANGUAGE sql IMMUTABLE AS $$
    SELECT CASE p_status WHEN 1 THEN 'Pending' WHEN 2 THEN 'Approved' WHEN 3 THEN 'Rejected' WHEN 4 THEN 'Complete' ELSE '** Invalid **' END::varchar(15)
$$;
