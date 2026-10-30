<!-- dbmig conversion prompt bundle
     batch: 4/4  units: ProductSales, ReferenceData, Shopping, ShoppingCart, ShoppingCartItem
     Convert each unit and SAVE PostgreSQL DDL to its output file:
       - ProductSales -> ddl/dbo/productsales.sql
       - ReferenceData -> ddl/dbo/referencedata.sql
       - Shopping -> ddl/dbo/shopping.sql
       - ShoppingCart -> ddl/dbo/shoppingcart.sql
       - ShoppingCartItem -> ddl/dbo/shoppingcartitem.sql
     Then set the unit's status to 'converted' in manifest-DBO.yaml. -->

=== CONTEXT ===
Shared schema context for this run: `migrations/<project>/02-construction/_context-schema.md`. Read it once per session if you have not already — it holds the customer-specific rules (highest precedence), datatype map, engine checks and playbook index this task relies on. Do not skip it.

=== TASK ===
Convert the following SQL Server object unit to PostgreSQL DDL. Return only valid PostgreSQL DDL, ready to execute. Do not include explanation outside SQL comments. Preserve table and column intent; choose appropriate PostgreSQL types, index types, and constraint forms based on the whole unit. Fold UPPERCASE identifiers to lower_case unquoted PostgreSQL identifiers unless quoting is required. Qualify every created object with the target schema `dbo` (derived from the source schema — do NOT use the connection's database/catalog name for qualification).

=== CONSTRUCTS DETECTED IN THIS PROMPT'S SOURCE (apply the matching guidance; open the named playbook file when the context is not enough, and cite it in the conversion log) ===
- IDENTITY → GENERATED ... AS IDENTITY; reset after load — see `skills/sqlserver-to-postgresql-playbook/references/tsql/identity-and-sequences.md`

--- SOURCE DDL (SQL Server) — dbo.ProductSales (~15 rows) ---
-- === TABLE ===
CREATE TABLE [dbo].[ProductSales] (
    [SaleID] numeric(18,0) NOT NULL,
    [ProductID] int NOT NULL,
    [SaleDate] date NOT NULL,
    [Quantity] numeric(10,0) NOT NULL,
    [UnitPrice] numeric(9,2) NOT NULL,
    [TotalAmount] numeric(11,2) NOT NULL,
    [CustomerID] int NOT NULL,
    [SalePrice] numeric(9,2),
    [RegionID] numeric(10,0)
);

--- SOURCE DDL (SQL Server) — dbo.ReferenceData (~24 rows) ---
-- === TABLE ===
CREATE TABLE [dbo].[ReferenceData] (
    [Id] int IDENTITY(1,1) NOT NULL,
    [DataType] int NOT NULL,
    [Text] nvarchar(max) NOT NULL,
    [CreatedBy] nvarchar(max) NOT NULL,
    [CreatedOn] datetime2 NOT NULL,
    [UpdatedOn] datetime2 NOT NULL
);

-- === CONSTRAINTS (PK / UNIQUE / CHECK) ===
ALTER TABLE [dbo].[ReferenceData] ADD CONSTRAINT [PK_ReferenceData] PRIMARY KEY ([Id]);

--- SOURCE DDL (SQL Server) — dbo.Shopping (~95 rows) ---
-- === TABLE ===
CREATE TABLE [dbo].[Shopping] (
    [OrderID] int NOT NULL,
    [CustomerID] int,
    [OrderDate] datetime,
    [TotalAmount] decimal(10,2),
    [Status] nvarchar(20)
);

-- === CONSTRAINTS (PK / UNIQUE / CHECK) ===
ALTER TABLE [dbo].[Shopping] ADD CONSTRAINT [PK__Shopping__C3905BAF415046C1] PRIMARY KEY ([OrderID]);

--- SOURCE DDL (SQL Server) — dbo.ShoppingCart (~0 rows) ---
-- === TABLE ===
CREATE TABLE [dbo].[ShoppingCart] (
    [Id] int IDENTITY(1,1) NOT NULL,
    [CorrelationId] nvarchar(max) NOT NULL,
    [CreatedBy] nvarchar(max) NOT NULL,
    [CreatedOn] datetime2 NOT NULL,
    [UpdatedOn] datetime2 NOT NULL
);

-- === CONSTRAINTS (PK / UNIQUE / CHECK) ===
ALTER TABLE [dbo].[ShoppingCart] ADD CONSTRAINT [PK_ShoppingCart] PRIMARY KEY ([Id]);

--- SOURCE DDL (SQL Server) — dbo.ShoppingCartItem (~0 rows) ---
-- === TABLE ===
CREATE TABLE [dbo].[ShoppingCartItem] (
    [Id] int IDENTITY(1,1) NOT NULL,
    [ShoppingCartId] int NOT NULL,
    [BookId] int NOT NULL,
    [Quantity] int NOT NULL,
    [WantToBuy] bit NOT NULL,
    [CreatedBy] nvarchar(max) NOT NULL,
    [CreatedOn] datetime2 NOT NULL,
    [UpdatedOn] datetime2 NOT NULL
);

-- === CONSTRAINTS (PK / UNIQUE / CHECK) ===
ALTER TABLE [dbo].[ShoppingCartItem] ADD CONSTRAINT [PK_ShoppingCartItem] PRIMARY KEY ([Id]);

-- === INDEXES ===
-- NONCLUSTERED
CREATE INDEX [IX_ShoppingCartItem_BookId] ON [dbo].[ShoppingCartItem] (BookId);
-- NONCLUSTERED
CREATE INDEX [IX_ShoppingCartItem_ShoppingCartId] ON [dbo].[ShoppingCartItem] (ShoppingCartId);

-- === FOREIGN KEYS ===
ALTER TABLE [dbo].[ShoppingCartItem] ADD CONSTRAINT [FK_ShoppingCartItem_Book_BookId] FOREIGN KEY ([BookId]) REFERENCES [dbo].[Book] ([Id]);
ALTER TABLE [dbo].[ShoppingCartItem] ADD CONSTRAINT [FK_ShoppingCartItem_ShoppingCart_ShoppingCartId] FOREIGN KEY ([ShoppingCartId]) REFERENCES [dbo].[ShoppingCart] ([Id]);
