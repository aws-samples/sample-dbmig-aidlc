<!-- dbmig code conversion prompt
     batch: 2/4
     Convert each object and SAVE PostgreSQL code to its output file:
       - VIEW dbo.VwCustomerShopping -> code/dbo/view__vwcustomershopping.sql
       - VIEW dbo.VwOpenCoupons -> code/dbo/view__vwopencoupons.sql
       - VIEW dbo.VwRegionalSales -> code/dbo/view__vwregionalsales.sql
       - VIEW dbo.VwTopMembers -> code/dbo/view__vwtopmembers.sql
     Then set each unit's status to 'converted' in code-manifest-DBO.yaml. -->

=== CONTEXT ===
Shared code context for this run: `migrations/<project>/02-construction/_context-code.md`. Read it once per session if you have not already — it holds the customer-specific rules (highest precedence), datatype map, engine checks and playbook index this task relies on. Do not skip it.

=== TASK ===
Convert the following SQL Server stored code object to PostgreSQL (PL/pgSQL). Return only valid PostgreSQL, ready to execute. Packages/modules have no direct equivalent: map each routine to its own function/procedure. Note any construct that needs human review in a SQL comment. Qualify every created object with the target schema `dbo` (derived from the source schema — do NOT use the connection's database/catalog name for qualification). Each object below is independent: convert each one and save it to its own output file (listed in the header).

=== CONSTRUCTS DETECTED IN THIS PROMPT'S SOURCE (apply the matching guidance; open the named playbook file when the context is not enough, and cite it in the conversion log) ===
- TOP → LIMIT (mind ORDER BY / WITH TIES) — see `skills/sqlserver-to-postgresql-playbook/references/tsql/top-fetch.md`
- date functions → interval arithmetic / date_part; DATEDIFF counts boundaries (current_date - d::date for DAY) — see `skills/sqlserver-to-postgresql-playbook/references/tsql/date-time-functions.md`
- CONVERT/FORMAT(MESSAGE) → CAST / to_char / format() (style codes and NULL rendering differ) — see `skills/sqlserver-to-postgresql-playbook/references/tsql/cast-and-convert.md`
- ISNULL/IIF/CHOOSE → COALESCE / CASE / array index
- TOP n PERCENT → row_number() <= ceil(count * n / 100) — see `skills/sqlserver-to-postgresql-playbook/references/tsql/top-fetch.md`
- CURRENT_USER/SUSER_SNAME → current_user/session_user (DB user vs login differ — BEHAVIOURAL)
- '+' string concatenation → '||' (NULL handling: CONCAT_NULL_YIELDS_NULL) — see `skills/sqlserver-to-postgresql-playbook/references/tsql/string-functions.md`

--- SOURCE (VIEW) — dbo.VwCustomerShopping ---
CREATE VIEW [dbo].[VwCustomerShopping] AS
SELECT 
    o.[OrderID],
    c.[FirstName] + ' ' + c.[LastName] AS [CustomerName],
    o.[OrderDate],
    o.[TotalAmount],
    o.[Status],
    FORMATMESSAGE(
        'Hi, %s! Your order #%s for $%s will be shipped shortly. Thank you!',
        c.[FirstName],
        CAST(o.[OrderID] AS VARCHAR),
        CAST(o.[TotalAmount] AS VARCHAR)
    ) AS [GreetingMessage]
FROM [dbo].[Shopping] o
JOIN [dbo].[Members] c ON c.[CustomerID] = o.[CustomerID];

--- SOURCE (VIEW) — dbo.VwOpenCoupons ---
CREATE VIEW [dbo].[VwOpenCoupons] AS
SELECT 
    t.[TicketID], 
    c.[FirstName], 
    c.[LastName], 
    t.[IssueDescription], 
    t.[CreatedDate], 
    DATEDIFF(DAY, t.[CreatedDate], GETDATE()) AS [DaysOpen]
FROM [dbo].[Coupons] t
JOIN [dbo].[Members] c ON t.[CustomerID] = c.[CustomerID]
WHERE t.[Status] = 'Open' AND t.[OSUser] = CURRENT_USER;

--- SOURCE (VIEW) — dbo.VwRegionalSales ---
CREATE VIEW [dbo].[VwRegionalSales] ([RegionName], [RegionSalesSum]) AS
SELECT 
    CHOOSE([RegionID], 
           'North America', 'Europe', 'Asia', 'South America', 'Africa', 
           'Australia', 'Middle East', 'Central America', 'Eastern Europe', 
           'Western Europe') AS [RegionName],
    SUM([Quantity] * [SalePrice]) AS [RegionSalesSum]
FROM [dbo].[ProductSales]
GROUP BY CHOOSE([RegionID], 
                'North America', 'Europe', 'Asia', 'South America', 'Africa', 
                'Australia', 'Middle East', 'Central America', 'Eastern Europe', 
                'Western Europe');

--- SOURCE (VIEW) — dbo.VwTopMembers ---
-- Create views
CREATE VIEW [dbo].[VwTopMembers] AS
SELECT * 
FROM (
    SELECT TOP 50 PERCENT 
        c.[CustomerID], 
        c.[FirstName], 
        c.[LastName], 
        SUM(o.[TotalAmount]) AS [TotalSpent]
    FROM [dbo].[Members] c
    JOIN [dbo].[Shopping] o ON c.[CustomerID] = o.[CustomerID]
    GROUP BY c.[CustomerID], c.[FirstName], c.[LastName]
    ORDER BY [TotalSpent] DESC
) sub;
