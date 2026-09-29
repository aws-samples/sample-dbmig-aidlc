-- SQL Server datetime has 1/300 s ticks: DATEADD(ms,-2,'2004-07-01') rounds to 23:59:59.997.
-- PostgreSQL timestamps are exact, so the rounded value is reproduced explicitly (checklist item 8).
CREATE OR REPLACE FUNCTION dbo.ufngetaccountingenddate()
RETURNS timestamp(3) LANGUAGE sql IMMUTABLE AS $$
    SELECT timestamp '2004-06-30 23:59:59.997'
$$;
