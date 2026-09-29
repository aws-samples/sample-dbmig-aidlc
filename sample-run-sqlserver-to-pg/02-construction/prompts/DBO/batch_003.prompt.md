<!-- dbmig conversion prompt bundle
     batch: 3/4  units: Order, OrderItem, Person, Product, ProductSaleRegions
     Convert each unit and SAVE PostgreSQL DDL to its output file:
       - Order -> ddl/dbo/order.sql
       - OrderItem -> ddl/dbo/orderitem.sql
       - Person -> ddl/dbo/person.sql
       - Product -> ddl/dbo/product.sql
       - ProductSaleRegions -> ddl/dbo/productsaleregions.sql
     Then set the unit's status to 'converted' in manifest-DBO.yaml. -->

=== CONTEXT ===
Shared schema context for this run: `migrations/<project>/02-construction/_context-schema.md`. Read it once per session if you have not already — it holds the customer-specific rules (highest precedence), datatype map, engine checks and playbook index this task relies on. Do not skip it.

=== TASK ===
Convert the following SQL Server object unit to PostgreSQL DDL. Return only valid PostgreSQL DDL, ready to execute. Do not include explanation outside SQL comments. Preserve table and column intent; choose appropriate PostgreSQL types, index types, and constraint forms based on the whole unit. Fold UPPERCASE identifiers to lower_case unquoted PostgreSQL identifiers unless quoting is required. Qualify every created object with the target schema `dbo` (derived from the source schema — do NOT use the connection's database/catalog name for qualification).

=== CONSTRUCTS DETECTED IN THIS OBJECT (apply the matching guidance in the context) ===
- IDENTITY → GENERATED ... AS IDENTITY; reset after load

--- SOURCE DDL (SQL Server) — dbo.Order (~0 rows) ---
-- === TABLE ===
CREATE TABLE [dbo].[Order] (
    [Id] int IDENTITY(1,1) NOT NULL,
    [CustomerId] int NOT NULL,
    [AddressId] int NOT NULL,
    [DeliveryDate] datetime2 NOT NULL,
    [OrderStatus] int NOT NULL,
    [CreatedBy] nvarchar(max) NOT NULL,
    [CreatedOn] datetime2 NOT NULL,
    [UpdatedOn] datetime2 NOT NULL
);

-- === CONSTRAINTS (PK / UNIQUE / CHECK) ===
ALTER TABLE [dbo].[Order] ADD CONSTRAINT [PK_Order] PRIMARY KEY ([Id]);

-- === INDEXES ===
-- NONCLUSTERED
CREATE INDEX [IX_Order_AddressId] ON [dbo].[Order] (AddressId);
-- NONCLUSTERED
CREATE INDEX [IX_Order_CustomerId] ON [dbo].[Order] (CustomerId);

-- === FOREIGN KEYS ===
ALTER TABLE [dbo].[Order] ADD CONSTRAINT [FK_Order_Address_AddressId] FOREIGN KEY ([AddressId]) REFERENCES [dbo].[Address] ([Id]);
ALTER TABLE [dbo].[Order] ADD CONSTRAINT [FK_Order_Customer_CustomerId] FOREIGN KEY ([CustomerId]) REFERENCES [dbo].[Customer] ([Id]);

--- SOURCE DDL (SQL Server) — dbo.OrderItem (~0 rows) ---
-- === TABLE ===
CREATE TABLE [dbo].[OrderItem] (
    [Id] int IDENTITY(1,1) NOT NULL,
    [OrderId] int NOT NULL,
    [BookId] int NOT NULL,
    [Quantity] int NOT NULL,
    [CreatedBy] nvarchar(max) NOT NULL,
    [CreatedOn] datetime2 NOT NULL,
    [UpdatedOn] datetime2 NOT NULL
);

-- === CONSTRAINTS (PK / UNIQUE / CHECK) ===
ALTER TABLE [dbo].[OrderItem] ADD CONSTRAINT [PK_OrderItem] PRIMARY KEY ([Id]);

-- === INDEXES ===
-- NONCLUSTERED
CREATE INDEX [IX_OrderItem_BookId] ON [dbo].[OrderItem] (BookId);
-- NONCLUSTERED
CREATE INDEX [IX_OrderItem_OrderId] ON [dbo].[OrderItem] (OrderId);

-- === FOREIGN KEYS ===
ALTER TABLE [dbo].[OrderItem] ADD CONSTRAINT [FK_OrderItem_Book_BookId] FOREIGN KEY ([BookId]) REFERENCES [dbo].[Book] ([Id]);
ALTER TABLE [dbo].[OrderItem] ADD CONSTRAINT [FK_OrderItem_Order_OrderId] FOREIGN KEY ([OrderId]) REFERENCES [dbo].[Order] ([Id]);

--- SOURCE DDL (SQL Server) — dbo.Person (~930 rows) ---
-- === TABLE ===
CREATE TABLE [dbo].[Person] (
    [BusinessEntityID] int NOT NULL,
    [PersonType] nchar(2) NOT NULL,
    [NameStyle] bit NOT NULL DEFAULT ((0)),
    [Title] nvarchar(8),
    [FirstName] nvarchar(100) NOT NULL,
    [MiddleName] nvarchar(100),
    [LastName] nvarchar(100) NOT NULL,
    [Suffix] nvarchar(10),
    [EmailPromotion] int NOT NULL DEFAULT ((0)),
    [AdditionalContactInfo] xml,
    [Demographics] xml,
    [rowguid] uniqueidentifier NOT NULL DEFAULT (newid()),
    [ModifiedDate] datetime NOT NULL DEFAULT (getdate())
);

-- === INDEXES ===
-- NONCLUSTERED
CREATE UNIQUE INDEX [AK_Person_rowguid] ON [dbo].[Person] (rowguid);
-- NONCLUSTERED
CREATE INDEX [IX_Person_LastName_FirstName_MiddleName] ON [dbo].[Person] (LastName, FirstName, MiddleName);

--- SOURCE DDL (SQL Server) — dbo.Product (~504 rows) ---
-- === TABLE ===
CREATE TABLE [dbo].[Product] (
    [ProductID] int IDENTITY(1,1) NOT NULL,
    [Name] nvarchar(100) NOT NULL,
    [ProductNumber] nvarchar(25) NOT NULL,
    [MakeFlag] bit NOT NULL DEFAULT ((1)),
    [FinishedGoodsFlag] bit NOT NULL DEFAULT ((1)),
    [Color] nvarchar(15),
    [SafetyStockLevel] smallint NOT NULL,
    [ReorderPoint] smallint NOT NULL,
    [StandardCost] money NOT NULL,
    [ListPrice] money NOT NULL,
    [Size] nvarchar(5),
    [SizeUnitMeasureCode] nchar(3),
    [WeightUnitMeasureCode] nchar(3),
    [Weight] decimal(8,2),
    [DaysToManufacture] int NOT NULL,
    [ProductLine] nchar(2),
    [Class] nchar(2),
    [Style] nchar(2),
    [ProductSubcategoryID] int,
    [ProductModelID] int,
    [SellStartDate] datetime NOT NULL,
    [SellEndDate] datetime,
    [DiscontinuedDate] datetime,
    [rowguid] uniqueidentifier NOT NULL DEFAULT (newid()),
    [ModifiedDate] datetime NOT NULL DEFAULT (getdate())
);

-- === CONSTRAINTS (PK / UNIQUE / CHECK) ===
ALTER TABLE [dbo].[Product] ADD CONSTRAINT [PK_Product_ProductID] PRIMARY KEY ([ProductID]);
ALTER TABLE [dbo].[Product] ADD CONSTRAINT [CK_Product_DaysToManufacture] CHECK ([DaysToManufacture]>=(0));
ALTER TABLE [dbo].[Product] ADD CONSTRAINT [CK_Product_ListPrice] CHECK ([ListPrice]>=(0.00));
ALTER TABLE [dbo].[Product] ADD CONSTRAINT [CK_Product_ReorderPoint] CHECK ([ReorderPoint]>(0));
ALTER TABLE [dbo].[Product] ADD CONSTRAINT [CK_Product_SafetyStockLevel] CHECK ([SafetyStockLevel]>(0));
ALTER TABLE [dbo].[Product] ADD CONSTRAINT [CK_Product_SellEndDate] CHECK ([SellEndDate]>=[SellStartDate] OR [SellEndDate] IS NULL);
ALTER TABLE [dbo].[Product] ADD CONSTRAINT [CK_Product_StandardCost] CHECK ([StandardCost]>=(0.00));
ALTER TABLE [dbo].[Product] ADD CONSTRAINT [CK_Product_Weight] CHECK ([Weight]>(0.00));

-- === INDEXES ===
-- NONCLUSTERED
CREATE UNIQUE INDEX [AK_Product_Name] ON [dbo].[Product] (Name);
-- NONCLUSTERED
CREATE UNIQUE INDEX [AK_Product_ProductNumber] ON [dbo].[Product] (ProductNumber);
-- NONCLUSTERED
CREATE UNIQUE INDEX [AK_Product_rowguid] ON [dbo].[Product] (rowguid);

--- SOURCE DDL (SQL Server) — dbo.ProductSaleRegions (~10 rows) ---
-- === TABLE ===
CREATE TABLE [dbo].[ProductSaleRegions] (
    [RegionID] int NOT NULL,
    [RegionName] varchar(50) NOT NULL
);
