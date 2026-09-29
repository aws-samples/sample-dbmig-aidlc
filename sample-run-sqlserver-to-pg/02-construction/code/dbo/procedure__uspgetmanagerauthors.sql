-- Result-set procedure -> set-returning FUNCTION (call: SELECT * FROM dbo.uspgetmanagerauthors(id)).
-- LEFT(x, LEN(x)-1) -> left(x, length(x) - 1). OPTION (MAXRECURSION 25) -> recursionlevel < 25
-- guard (BEHAVIOURAL: SQL Server raises an error past 25 levels; the guard stops silently).
CREATE OR REPLACE FUNCTION dbo.uspgetmanagerauthors(p_businessentityid integer)
RETURNS TABLE (recursionlevel integer, organizationnode varchar, managerfirstname varchar, managerlastname varchar, businessentityid integer, firstname varchar, lastname varchar)
LANGUAGE sql STABLE AS $$
    WITH RECURSIVE emp_cte (businessentityid, organizationnode, firstname, lastname, recursionlevel) AS (
        SELECT e.businessentityid, e.organizationnode, p.firstname, p.lastname, 0
        FROM dbo.author e JOIN dbo.person p ON p.businessentityid = e.businessentityid
        WHERE e.businessentityid = p_businessentityid
        UNION ALL
        SELECT e.businessentityid, e.organizationnode, p.firstname, p.lastname, emp_cte.recursionlevel + 1
        FROM dbo.author e
        JOIN emp_cte ON e.organizationnode = left(emp_cte.organizationnode, length(emp_cte.organizationnode) - 1)
        JOIN dbo.person p ON p.businessentityid = e.businessentityid
        WHERE emp_cte.recursionlevel < 25
    )
    SELECT emp_cte.recursionlevel, emp_cte.organizationnode, p.firstname, p.lastname, emp_cte.businessentityid, emp_cte.firstname, emp_cte.lastname
    FROM emp_cte
    JOIN dbo.author e ON e.organizationnode = left(emp_cte.organizationnode, length(emp_cte.organizationnode) - 1)
    JOIN dbo.person p ON p.businessentityid = e.businessentityid
    ORDER BY emp_cte.recursionlevel, emp_cte.organizationnode
$$;
