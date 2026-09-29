-- tinyint (0-255) -> integer parameter: a smallint parameter does not resolve for callers passing an
-- integer literal (PostgreSQL will not implicitly narrow integer -> smallint in function lookup).
CREATE OR REPLACE FUNCTION dbo.ufngetsalesorderstatustext(p_status integer)
RETURNS varchar(15) LANGUAGE sql IMMUTABLE AS $$
    SELECT CASE p_status WHEN 1 THEN 'In process' WHEN 2 THEN 'Approved' WHEN 3 THEN 'Backordered' WHEN 4 THEN 'Rejected' WHEN 5 THEN 'Shipped' WHEN 6 THEN 'Cancelled' ELSE '** Invalid **' END::varchar(15)
$$;
