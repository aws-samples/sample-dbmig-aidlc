-- DATEDIFF(DAY, x, GETDATE()) -> current_date - x::date.
-- BEHAVIOURAL: CURRENT_USER is the SQL Server *database user* (e.g. 'dbo'); PostgreSQL returns the
-- login role (e.g. 'postgres'). Rows filtered on osuser = CURRENT_USER differ between engines unless
-- the coupon owners are re-mapped to PostgreSQL roles — review with the application owner.
CREATE OR REPLACE VIEW dbo.vwopencoupons AS
SELECT t.ticketid, c.firstname, c.lastname, t.issuedescription, t.createddate,
       (current_date - t.createddate::date) AS daysopen
FROM dbo.coupons t
JOIN dbo.members c ON t.customerid = c.customerid
WHERE t.status = 'Open' AND t.osuser = current_user;
