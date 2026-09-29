-- Result-set procedure -> set-returning FUNCTION (call: SELECT * FROM dbo.uspgetauthormanagers(id)).
-- LEFT(x, LEN(x)-1) -> left(x, length(x) - 1). OPTION (MAXRECURSION 25) -> recursionlevel < 25
-- guard (BEHAVIOURAL: SQL Server raises an error past 25 levels; the guard stops silently).
CREATE OR REPLACE FUNCTION dbo.uspgetauthormanagers(p_businessentityid integer)
RETURNS TABLE (recursionlevel integer, businessentityid integer, firstname varchar, lastname varchar, organizationnode varchar, managerfirstname varchar, managerlastname varchar)
LANGUAGE sql STABLE AS $$
    WITH RECURSIVE emp_cte (businessentityid, organizationnode, firstname, lastname, jobtitle, recursionlevel) AS (
        SELECT e.businessentityid, e.organizationnode, p.firstname, p.lastname, e.jobtitle, 0
        FROM dbo.author e JOIN dbo.person p ON p.businessentityid = e.businessentityid
        WHERE e.businessentityid = p_businessentityid
        UNION ALL
        SELECT e.businessentityid, e.organizationnode, p.firstname, p.lastname, e.jobtitle, emp_cte.recursionlevel + 1
        FROM dbo.author e
        JOIN emp_cte ON left(e.organizationnode, length(e.organizationnode) - 1) = emp_cte.organizationnode
        JOIN dbo.person p ON p.businessentityid = e.businessentityid
        WHERE emp_cte.recursionlevel < 25
    )
    SELECT emp_cte.recursionlevel, emp_cte.businessentityid, emp_cte.firstname, emp_cte.lastname, emp_cte.organizationnode, p.firstname, p.lastname
    FROM emp_cte
    JOIN dbo.author e ON left(emp_cte.organizationnode, length(emp_cte.organizationnode) - 1) = e.organizationnode
    JOIN dbo.person p ON p.businessentityid = e.businessentityid
    ORDER BY emp_cte.recursionlevel, emp_cte.organizationnode
$$;
