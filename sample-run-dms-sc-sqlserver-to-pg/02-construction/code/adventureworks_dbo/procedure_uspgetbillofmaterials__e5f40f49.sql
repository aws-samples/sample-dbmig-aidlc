CREATE OR REPLACE PROCEDURE adventureworks_dbo.uspgetbillofmaterials(IN par_startproductid INTEGER, IN par_checkdate TIMESTAMP WITHOUT TIME ZONE, INOUT p_refcur refcursor)
AS 
$BODY$
BEGIN
    /* Use recursive query to generate a multi-level Bill of Material (i.e. all level 1 */
    /* components of a level 0 assembly, all level 2 components of a level 1 assembly) */
    /* The CheckDate eliminates any components that are no longer used in the product on this date. */
    OPEN p_refcur FOR
    WITH RECURSIVE bom_cte (productassemblyid, componentid, componentdesc, perassemblyqty, standardcost, listprice, bomlevel, recursionlevel)
    AS (
    /* CTE name and columns */
    SELECT
        b.productassemblyid, b.componentid, p.name, b.perassemblyqty, p.standardcost, p.listprice, b.bomlevel, 0
        /* Get the initial list of components for the bike assembly */
        FROM adventureworks_production.billofmaterials AS b
        INNER JOIN adventureworks_production.product AS p
            ON b.componentid = p.productid
        WHERE b.productassemblyid = par_StartProductID AND par_CheckDate >= b.startdate AND par_CheckDate <= COALESCE(b.enddate, par_CheckDate)
    UNION ALL
    SELECT
        b.productassemblyid, b.componentid, p.name, b.perassemblyqty, p.standardcost, p.listprice, b.bomlevel, recursionlevel + 1
        /* Join recursive member to anchor */
        FROM bom_cte AS cte
        INNER JOIN adventureworks_production.billofmaterials AS b
            ON b.productassemblyid = cte.componentid
        INNER JOIN adventureworks_production.product AS p
            ON b.componentid = p.productid
        WHERE par_CheckDate >= b.startdate AND par_CheckDate <= COALESCE(b.enddate, par_CheckDate))
    /* Outer select from the CTE */
    SELECT
        b.productassemblyid, b.componentid, b.componentdesc, SUM(b.perassemblyqty) AS totalquantity, b.standardcost, b.listprice, b.bomlevel, b.recursionlevel
        FROM bom_cte AS b
        GROUP BY b.componentid, b.componentdesc, b.productassemblyid, b.bomlevel, b.recursionlevel, b.standardcost, b.listprice
        ORDER BY b.bomlevel NULLS FIRST, b.productassemblyid NULLS FIRST, b.componentid NULLS FIRST;
END;
$BODY$
LANGUAGE plpgsql;