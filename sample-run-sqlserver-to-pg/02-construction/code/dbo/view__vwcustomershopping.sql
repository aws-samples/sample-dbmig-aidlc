-- '+' concat -> '||' (both yield NULL when an operand is NULL: CONCAT_NULL_YIELDS_NULL ON).
-- FORMATMESSAGE -> format(); FORMATMESSAGE renders a NULL argument as '(null)', format() as ''
-- -> coalesce(...,'(null)') keeps SQL Server's output.
CREATE OR REPLACE VIEW dbo.vwcustomershopping AS
SELECT o.orderid,
       c.firstname || ' ' || c.lastname AS customername,
       o.orderdate, o.totalamount, o.status,
       format('Hi, %s! Your order #%s for $%s will be shipped shortly. Thank you!',
              coalesce(c.firstname, '(null)'), coalesce(o.orderid::varchar, '(null)'),
              coalesce(o.totalamount::varchar, '(null)')) AS greetingmessage
FROM dbo.shopping o
JOIN dbo.members c ON c.customerid = o.customerid;
