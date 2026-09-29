-- Result-set procedure -> set-returning FUNCTION (call: SELECT * FROM dbo.uspgetbillofmaterials(id, date)).
-- ISNULL -> coalesce. MAXRECURSION 25 -> recursionlevel < 25 guard (see uspgetauthormanagers).
-- RETURNS TABLE types match the converted columns / aggregates exactly (SUM(numeric) = numeric).
CREATE OR REPLACE FUNCTION dbo.uspgetbillofmaterials(p_startproductid integer, p_checkdate timestamp(3))
RETURNS TABLE (productassemblyid integer, componentid integer, componentdesc varchar, totalquantity numeric,
               standardcost numeric, listprice numeric, bomlevel smallint, recursionlevel integer)
LANGUAGE sql STABLE AS $$
    WITH RECURSIVE bom_cte (productassemblyid, componentid, componentdesc, perassemblyqty, standardcost, listprice, bomlevel, recursionlevel) AS (
        SELECT b.productassemblyid, b.componentid, p.name, b.perassemblyqty, p.standardcost, p.listprice, b.bomlevel, 0
        FROM dbo.billofmaterials b JOIN dbo.product p ON b.componentid = p.productid
        WHERE b.productassemblyid = p_startproductid AND p_checkdate >= b.startdate AND p_checkdate <= coalesce(b.enddate, p_checkdate)
        UNION ALL
        SELECT b.productassemblyid, b.componentid, p.name, b.perassemblyqty, p.standardcost, p.listprice, b.bomlevel, cte.recursionlevel + 1
        FROM bom_cte cte
        JOIN dbo.billofmaterials b ON b.productassemblyid = cte.componentid
        JOIN dbo.product p ON b.componentid = p.productid
        WHERE p_checkdate >= b.startdate AND p_checkdate <= coalesce(b.enddate, p_checkdate)
          AND cte.recursionlevel < 25
    )
    SELECT b.productassemblyid, b.componentid, b.componentdesc::varchar, sum(b.perassemblyqty),
           b.standardcost, b.listprice, b.bomlevel, b.recursionlevel
    FROM bom_cte b
    GROUP BY b.componentid, b.componentdesc, b.productassemblyid, b.bomlevel, b.recursionlevel, b.standardcost, b.listprice
    ORDER BY b.bomlevel, b.productassemblyid, b.componentid
$$;
