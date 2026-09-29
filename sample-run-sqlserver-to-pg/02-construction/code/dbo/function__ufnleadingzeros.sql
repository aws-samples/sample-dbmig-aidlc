-- REPLICATE('0', 8 - DATALENGTH(v)) + v  ->  lpad(v, 8, '0'). WITH SCHEMABINDING dropped.
-- Values wider than 8 chars: SQL Server CONVERT(varchar(8), int) yields '*' (overflow marker),
-- DATALENGTH('*') = 1, so the result is REPLICATE('0', 7) + '*' = '0000000*' — reproduced.
CREATE OR REPLACE FUNCTION dbo.ufnleadingzeros(p_value integer)
RETURNS varchar(8) LANGUAGE sql IMMUTABLE AS $$
    SELECT CASE WHEN length(p_value::text) > 8 THEN '0000000*' ELSE lpad(p_value::text, 8, '0') END::varchar(8)
$$;
