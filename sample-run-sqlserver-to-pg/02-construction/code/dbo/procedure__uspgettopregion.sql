-- Result-set procedure -> set-returning FUNCTION. The five "TOP n PERCENT ... WHERE @Percent = n"
-- branches select ceil(n% of rows) by NumberOfSales DESC; any other @Percent returns no rows.
-- The LEFT JOIN is effectively inner (WHERE on ps.saledate) — preserved as written.
-- COUNT() returns bigint in PostgreSQL (int in SQL Server). Ties at the cut-off are arbitrary.
CREATE OR REPLACE FUNCTION dbo.uspgettopregion(p_percent integer)
RETURNS TABLE (regionid integer, regionname varchar, numberofsales bigint, totalsalesamount numeric, numberofmembers bigint)
LANGUAGE sql STABLE AS $$
    WITH halfyearsales AS (
        SELECT psr.regionid, psr.regionname::varchar AS regionname, count(ps.saleid) AS numberofsales,
               sum(ps.totalamount) AS totalsalesamount, count(DISTINCT ps.customerid) AS numberofmembers
        FROM dbo.productsaleregions psr
        LEFT JOIN dbo.productsales ps ON psr.regionid = ps.regionid
        WHERE ps.saledate >= (localtimestamp - interval '6 months')
        GROUP BY psr.regionid, psr.regionname
    ), ranked AS (
        SELECT h.*, row_number() OVER (ORDER BY h.numberofsales DESC) AS rn, count(*) OVER () AS cnt
        FROM halfyearsales h
    )
    SELECT regionid, regionname, numberofsales, totalsalesamount, numberofmembers
    FROM ranked
    WHERE p_percent IN (10, 20, 30, 40, 50) AND rn <= ceil(cnt * p_percent / 100.0)
    ORDER BY numberofsales DESC, totalsalesamount DESC
$$;
