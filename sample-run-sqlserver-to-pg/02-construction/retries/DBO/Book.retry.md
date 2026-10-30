<!-- dbmig conversion prompt bundle
     batch: 1/4  units: Address, Author, BillOfMaterials, Book, Coupons
     Convert each unit and SAVE PostgreSQL DDL to its output file:
       - Address -> ddl/dbo/address.sql
       - Author -> ddl/dbo/author.sql
       - BillOfMaterials -> ddl/dbo/billofmaterials.sql
       - Book -> ddl/dbo/book.sql
       - Coupons -> ddl/dbo/coupons.sql
     Then set the unit's status to 'converted' in manifest-DBO.yaml. -->

=== CONTEXT ===
Shared schema context for this run: `migrations/<project>/02-construction/_context-schema.md`. Read it once per session if you have not already — it holds the customer-specific rules (highest precedence), datatype map, engine checks and playbook index this task relies on. Do not skip it.

=== TASK ===
Convert the following SQL Server object unit to PostgreSQL DDL. Return only valid PostgreSQL DDL, ready to execute. Do not include explanation outside SQL comments. Preserve table and column intent; choose appropriate PostgreSQL types, index types, and constraint forms based on the whole unit. Fold UPPERCASE identifiers to lower_case unquoted PostgreSQL identifiers unless quoting is required. Qualify every created object with the target schema `dbo` (derived from the source schema — do NOT use the connection's database/catalog name for qualification).

=== CONSTRUCTS DETECTED IN THIS PROMPT'S SOURCE (apply the matching guidance; open the named playbook file when the context is not enough, and cite it in the conversion log) ===
- IDENTITY → GENERATED ... AS IDENTITY; reset after load — see `skills/sqlserver-to-postgresql-playbook/references/tsql/identity-and-sequences.md`
- date functions → interval arithmetic / date_part; DATEDIFF counts boundaries (current_date - d::date for DAY) — see `skills/sqlserver-to-postgresql-playbook/references/tsql/date-time-functions.md`

--- SOURCE DDL (SQL Server) — dbo.Address (~0 rows) ---
-- === TABLE ===
CREATE TABLE [dbo].[Address] (
    [Id] int IDENTITY(1,1) NOT NULL,
    [AddressLine1] nvarchar(max) NOT NULL,
    [AddressLine2] nvarchar(max),
    [City] nvarchar(max) NOT NULL,
    [State] nvarchar(max) NOT NULL,
    [Country] nvarchar(max) NOT NULL,
    [ZipCode] nvarchar(max) NOT NULL,
    [CustomerId] int NOT NULL,
    [IsActive] bit NOT NULL,
    [CreatedBy] nvarchar(max) NOT NULL,
    [CreatedOn] datetime2 NOT NULL,
    [UpdatedOn] datetime2 NOT NULL
);

-- === CONSTRAINTS (PK / UNIQUE / CHECK) ===
ALTER TABLE [dbo].[Address] ADD CONSTRAINT [PK_Address] PRIMARY KEY ([Id]);

-- === INDEXES ===
-- NONCLUSTERED
CREATE INDEX [IX_Address_CustomerId] ON [dbo].[Address] (CustomerId);

-- === FOREIGN KEYS ===
ALTER TABLE [dbo].[Address] ADD CONSTRAINT [FK_Address_Customer_CustomerId] FOREIGN KEY ([CustomerId]) REFERENCES [dbo].[Customer] ([Id]);

--- SOURCE DDL (SQL Server) — dbo.Author (~290 rows) ---
-- === TABLE ===
CREATE TABLE [dbo].[Author] (
    [BusinessEntityID] int IDENTITY(1,1) NOT NULL,
    [NationalIDNumber] nvarchar(15) NOT NULL,
    [LoginID] nvarchar(256) NOT NULL,
    [OrganizationNode] nvarchar(50),
    [JobTitle] nvarchar(50) NOT NULL,
    [BirthDate] date NOT NULL,
    [MaritalStatus] nchar(1) NOT NULL,
    [Gender] nchar(1) NOT NULL,
    [HireDate] date NOT NULL,
    [VacationHours] smallint NOT NULL DEFAULT ((0)),
    [CurrentFlag] bit NOT NULL DEFAULT ((1)),
    [ModifiedDate] datetime NOT NULL DEFAULT (getdate())
);

-- === CONSTRAINTS (PK / UNIQUE / CHECK) ===
ALTER TABLE [dbo].[Author] ADD CONSTRAINT [PK_Author_BusinessEntityID] PRIMARY KEY ([BusinessEntityID]);
ALTER TABLE [dbo].[Author] ADD CONSTRAINT [CK_Author_BirthDate] CHECK ([BirthDate]>='1930-01-01' AND [BirthDate]<=dateadd(year,(-18),getdate()));
ALTER TABLE [dbo].[Author] ADD CONSTRAINT [CK_Author_HireDate] CHECK ([HireDate]>='1996-07-01' AND [HireDate]<=dateadd(day,(1),getdate()));
ALTER TABLE [dbo].[Author] ADD CONSTRAINT [CK_Author_VacationHours] CHECK ([VacationHours]>=(-40) AND [VacationHours]<=(240));

-- === INDEXES ===
-- NONCLUSTERED
CREATE UNIQUE INDEX [AK_Author_LoginID] ON [dbo].[Author] (LoginID);
-- NONCLUSTERED
CREATE UNIQUE INDEX [AK_Author_NationalIDNumber] ON [dbo].[Author] (NationalIDNumber);
-- NONCLUSTERED
CREATE INDEX [IX_Author_OrganizationNode] ON [dbo].[Author] (OrganizationNode);

--- SOURCE DDL (SQL Server) — dbo.BillOfMaterials (~982 rows) ---
-- === TABLE ===
CREATE TABLE [dbo].[BillOfMaterials] (
    [BillOfMaterialsID] int IDENTITY(1,1) NOT NULL,
    [ProductAssemblyID] int,
    [ComponentID] int NOT NULL,
    [StartDate] datetime NOT NULL DEFAULT (getdate()),
    [EndDate] datetime,
    [UnitMeasureCode] nchar(3) NOT NULL,
    [BOMLevel] smallint NOT NULL,
    [PerAssemblyQty] decimal(8,2) NOT NULL DEFAULT ((1.00)),
    [ModifiedDate] datetime NOT NULL DEFAULT (getdate())
);

-- === CONSTRAINTS (PK / UNIQUE / CHECK) ===
ALTER TABLE [dbo].[BillOfMaterials] ADD CONSTRAINT [PK_BillOfMaterials_BillOfMaterialsID] PRIMARY KEY ([BillOfMaterialsID]);
ALTER TABLE [dbo].[BillOfMaterials] ADD CONSTRAINT [CK_BillOfMaterials_EndDate] CHECK ([EndDate]>[StartDate] OR [EndDate] IS NULL);
ALTER TABLE [dbo].[BillOfMaterials] ADD CONSTRAINT [CK_BillOfMaterials_PerAssemblyQty] CHECK ([PerAssemblyQty]>=(1.00));
ALTER TABLE [dbo].[BillOfMaterials] ADD CONSTRAINT [CK_BillOfMaterials_ProductAssemblyID] CHECK ([ProductAssemblyID]<>[ComponentID]);

-- === INDEXES ===
-- NONCLUSTERED
CREATE UNIQUE INDEX [AK_BillOfMaterials_ProductAssemblyID_ComponentID_StartDate] ON [dbo].[BillOfMaterials] (ProductAssemblyID, ComponentID, StartDate);
-- NONCLUSTERED
CREATE INDEX [IX_BillOfMaterials_UnitMeasureCode] ON [dbo].[BillOfMaterials] (UnitMeasureCode);

--- SOURCE DDL (SQL Server) — dbo.Book (~8 rows) ---
-- === TABLE ===
CREATE TABLE [dbo].[Book] (
    [Id] int IDENTITY(1,1) NOT NULL,
    [Name] nvarchar(max) NOT NULL,
    [Author] nvarchar(max) NOT NULL,
    [Year] int,
    [ISBN] nvarchar(max) NOT NULL,
    [PublisherId] int NOT NULL,
    [BookTypeId] int NOT NULL,
    [GenreId] int NOT NULL,
    [ConditionId] int NOT NULL,
    [CoverImageUrl] nvarchar(max),
    [Summary] nvarchar(max),
    [Price] decimal(18,2) NOT NULL,
    [Quantity] int NOT NULL,
    [CreatedBy] nvarchar(max) NOT NULL,
    [CreatedOn] datetime2 NOT NULL,
    [UpdatedOn] datetime2 NOT NULL
);

-- === CONSTRAINTS (PK / UNIQUE / CHECK) ===
ALTER TABLE [dbo].[Book] ADD CONSTRAINT [PK_Book] PRIMARY KEY ([Id]);

-- === INDEXES ===
-- NONCLUSTERED
CREATE INDEX [IX_Book_BookTypeId] ON [dbo].[Book] (BookTypeId);
-- NONCLUSTERED
CREATE INDEX [IX_Book_ConditionId] ON [dbo].[Book] (ConditionId);
-- NONCLUSTERED
CREATE INDEX [IX_Book_GenreId] ON [dbo].[Book] (GenreId);
-- NONCLUSTERED
CREATE INDEX [IX_Book_PublisherId] ON [dbo].[Book] (PublisherId);

--- SOURCE DDL (SQL Server) — dbo.Coupons (~54 rows) ---
-- === TABLE ===
CREATE TABLE [dbo].[Coupons] (
    [TicketID] int NOT NULL,
    [CustomerID] int,
    [OrderID] int,
    [IssueDescription] nvarchar(max),
    [CreatedDate] datetime,
    [ResolvedDate] datetime,
    [Status] nvarchar(20),
    [OSUser] varchar(10)
);

-- === CONSTRAINTS (PK / UNIQUE / CHECK) ===
ALTER TABLE [dbo].[Coupons] ADD CONSTRAINT [PK__Coupons__712CC627862066EA] PRIMARY KEY ([TicketID]);

=== RETRY 3/3 — PREVIOUS ATTEMPT FAILED ===
The DDL you generated previously (below) FAILED to apply to the target database. Produce a CORRECTED version that runs on the target. Return only the corrected DDL (fenced or plain), targeting the same object(s). Diagnose the specific cause shown in the error and fix it (e.g. unsupported function, type, or syntax; if a feature/extension is unavailable, choose a supported alternative).

--- PREVIOUS DDL (failed) ---
CREATE EXTENSION IF NOT EXISTS dbo.citext SCHEMA dbo;  -- type referenced as dbo.citext: the apply session's search_path does not include dbo  -- must be on the app's search_path, see conversion log
-- case_insensitive_collation decision (option a): columns the application SEARCHES are dbo.citext so
-- LIKE keeps SQL Server's _CI_ behaviour (EF .Contains). `=` against a text-typed parameter stays
-- case-sensitive — see the conversion log.
CREATE TABLE dbo.book (
  id integer GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
  name dbo.citext NOT NULL, author dbo.citext NOT NULL, year integer, isbn dbo.citext NOT NULL,
  publisherid integer NOT NULL, booktypeid integer NOT NULL, genreid integer NOT NULL, conditionid integer NOT NULL,
  coverimageurl text, summary text, price numeric(18,2) NOT NULL, quantity integer NOT NULL,
  createdby text NOT NULL, createdon timestamp(6) NOT NULL, updatedon timestamp(6) NOT NULL
);
CREATE INDEX ix_book_booktypeid ON dbo.book (booktypeid);
CREATE INDEX ix_book_conditionid ON dbo.book (conditionid);
CREATE INDEX ix_book_genreid ON dbo.book (genreid);
CREATE INDEX ix_book_publisherid ON dbo.book (publisherid);

--- TARGET DATABASE ERROR ---
syntax error at or near "."
LINE 1: CREATE EXTENSION IF NOT EXISTS dbo.citext SCHEMA dbo;
                                          ^
