-- TOP 50 PERCENT ... ORDER BY -> first ceil(50% of rows) by row_number over the same order.
-- BEHAVIOURAL: ties at the cut-off are broken arbitrarily in both engines (no WITH TIES).
CREATE OR REPLACE VIEW dbo.vwtopmembers AS
SELECT customerid, firstname, lastname, totalspent
FROM (
    SELECT c.customerid, c.firstname, c.lastname, sum(o.totalamount) AS totalspent,
           row_number() OVER (ORDER BY sum(o.totalamount) DESC) AS rn,
           count(*) OVER () AS cnt
    FROM dbo.members c
    JOIN dbo.shopping o ON c.customerid = o.customerid
    GROUP BY c.customerid, c.firstname, c.lastname
) sub
WHERE rn <= ceil(cnt * 50 / 100.0);
