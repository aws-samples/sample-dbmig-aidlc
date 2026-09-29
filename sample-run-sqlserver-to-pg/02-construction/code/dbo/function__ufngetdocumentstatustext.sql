-- tinyint (0-255) -> integer parameter: a smallint parameter does not resolve for callers passing an
-- integer literal (PostgreSQL will not implicitly narrow integer -> smallint in function lookup).
CREATE OR REPLACE FUNCTION dbo.ufngetdocumentstatustext(p_status integer)
RETURNS varchar(16) LANGUAGE sql IMMUTABLE AS $$
    SELECT CASE p_status WHEN 1 THEN 'Pending approval' WHEN 2 THEN 'Approved' WHEN 3 THEN 'Obsolete' ELSE '** Invalid **' END::varchar(16)
$$;
