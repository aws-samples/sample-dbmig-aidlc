<!-- dbmig conversion prompt bundle
     batch: 2/4  units: Customer, DatabaseLog, ErrorLog, Members, Offer
     Convert each unit and SAVE PostgreSQL DDL to its output file:
       - Customer -> ddl/dbo/customer.sql
       - DatabaseLog -> ddl/dbo/databaselog.sql
       - ErrorLog -> ddl/dbo/errorlog.sql
       - Members -> ddl/dbo/members.sql
       - Offer -> ddl/dbo/offer.sql
     Then set the unit's status to 'converted' in manifest-DBO.yaml. -->

=== CONTEXT ===
Shared schema context for this run: `migrations/<project>/02-construction/_context-schema.md`. Read it once per session if you have not already — it holds the customer-specific rules (highest precedence), datatype map, engine checks and playbook index this task relies on. Do not skip it.

=== TASK ===
Convert the following SQL Server object unit to PostgreSQL DDL. Return only valid PostgreSQL DDL, ready to execute. Do not include explanation outside SQL comments. Preserve table and column intent; choose appropriate PostgreSQL types, index types, and constraint forms based on the whole unit. Fold UPPERCASE identifiers to lower_case unquoted PostgreSQL identifiers unless quoting is required. Qualify every created object with the target schema `dbo` (derived from the source schema — do NOT use the connection's database/catalog name for qualification).

=== CONSTRUCTS DETECTED IN THIS PROMPT'S SOURCE (apply the matching guidance; open the named playbook file when the context is not enough, and cite it in the conversion log) ===
- IDENTITY → GENERATED ... AS IDENTITY; reset after load — see `skills/sqlserver-to-postgresql-playbook/references/tsql/identity-and-sequences.md`
- date functions → interval arithmetic / date_part; DATEDIFF counts boundaries (current_date - d::date for DAY) — see `skills/sqlserver-to-postgresql-playbook/references/tsql/date-time-functions.md`

--- SOURCE DDL (SQL Server) — dbo.Customer (~1 rows) ---
-- === TABLE ===
CREATE TABLE [dbo].[Customer] (
    [Id] int IDENTITY(1,1) NOT NULL,
    [Sub] nvarchar(450) NOT NULL,
    [Username] nvarchar(max),
    [FirstName] nvarchar(max),
    [LastName] nvarchar(max),
    [Email] nvarchar(max),
    [DateOfBirth] datetime2,
    [Phone] nvarchar(max),
    [CreatedBy] nvarchar(max) NOT NULL,
    [CreatedOn] datetime2 NOT NULL,
    [UpdatedOn] datetime2 NOT NULL
);

-- === CONSTRAINTS (PK / UNIQUE / CHECK) ===
ALTER TABLE [dbo].[Customer] ADD CONSTRAINT [PK_Customer] PRIMARY KEY ([Id]);

-- === INDEXES ===
-- NONCLUSTERED
CREATE UNIQUE INDEX [IX_Customer_Sub] ON [dbo].[Customer] (Sub);

--- SOURCE DDL (SQL Server) — dbo.DatabaseLog (~30 rows) ---
-- === TABLE ===
CREATE TABLE [dbo].[DatabaseLog] (
    [DatabaseLogID] int IDENTITY(1,1) NOT NULL,
    [PostTime] datetime NOT NULL,
    [DatabaseUser] nvarchar(128) NOT NULL,
    [Event] nvarchar(128) NOT NULL,
    [Schema] nvarchar(128),
    [Object] nvarchar(128),
    [TSQL] nvarchar(max) NOT NULL,
    [XmlEvent] xml NOT NULL
);

-- === CONSTRAINTS (PK / UNIQUE / CHECK) ===
ALTER TABLE [dbo].[DatabaseLog] ADD CONSTRAINT [PK_DatabaseLog_DatabaseLogID] PRIMARY KEY ([DatabaseLogID]);

--- SOURCE DDL (SQL Server) — dbo.ErrorLog (~0 rows) ---
-- === TABLE ===
CREATE TABLE [dbo].[ErrorLog] (
    [ErrorLogID] int IDENTITY(1,1) NOT NULL,
    [ErrorTime] datetime NOT NULL DEFAULT (getdate()),
    [UserName] nvarchar(128) NOT NULL,
    [ErrorNumber] int NOT NULL,
    [ErrorSeverity] int,
    [ErrorState] int,
    [ErrorProcedure] nvarchar(126),
    [ErrorLine] int,
    [ErrorMessage] nvarchar(4000) NOT NULL
);

-- === CONSTRAINTS (PK / UNIQUE / CHECK) ===
ALTER TABLE [dbo].[ErrorLog] ADD CONSTRAINT [PK_ErrorLog_ErrorLogID] PRIMARY KEY ([ErrorLogID]);

--- SOURCE DDL (SQL Server) — dbo.Members (~20 rows) ---
-- === TABLE ===
CREATE TABLE [dbo].[Members] (
    [CustomerID] int NOT NULL,
    [FirstName] nvarchar(50),
    [LastName] nvarchar(50),
    [Email] nvarchar(100),
    [Phone] nvarchar(20),
    [RegistrationDate] date,
    [TotalOrderSum] decimal(10,2)
);

-- === CONSTRAINTS (PK / UNIQUE / CHECK) ===
ALTER TABLE [dbo].[Members] ADD CONSTRAINT [PK__Members__A4AE64B88BE371E3] PRIMARY KEY ([CustomerID]);

--- SOURCE DDL (SQL Server) — dbo.Offer (~0 rows) ---
-- === TABLE ===
CREATE TABLE [dbo].[Offer] (
    [Id] int IDENTITY(1,1) NOT NULL,
    [Author] nvarchar(max) NOT NULL,
    [ISBN] nvarchar(max) NOT NULL,
    [BookName] nvarchar(max) NOT NULL,
    [FrontUrl] nvarchar(max),
    [GenreId] int NOT NULL,
    [ConditionId] int NOT NULL,
    [PublisherId] int NOT NULL,
    [BookTypeId] int NOT NULL,
    [Summary] nvarchar(max),
    [OfferStatus] int NOT NULL,
    [Comment] nvarchar(max),
    [CustomerId] int NOT NULL,
    [BookPrice] decimal(18,2) NOT NULL,
    [CreatedBy] nvarchar(max) NOT NULL,
    [CreatedOn] datetime2 NOT NULL,
    [UpdatedOn] datetime2 NOT NULL
);

-- === CONSTRAINTS (PK / UNIQUE / CHECK) ===
ALTER TABLE [dbo].[Offer] ADD CONSTRAINT [PK_Offer] PRIMARY KEY ([Id]);

-- === INDEXES ===
-- NONCLUSTERED
CREATE INDEX [IX_Offer_BookTypeId] ON [dbo].[Offer] (BookTypeId);
-- NONCLUSTERED
CREATE INDEX [IX_Offer_ConditionId] ON [dbo].[Offer] (ConditionId);
-- NONCLUSTERED
CREATE INDEX [IX_Offer_CustomerId] ON [dbo].[Offer] (CustomerId);
-- NONCLUSTERED
CREATE INDEX [IX_Offer_GenreId] ON [dbo].[Offer] (GenreId);
-- NONCLUSTERED
CREATE INDEX [IX_Offer_PublisherId] ON [dbo].[Offer] (PublisherId);

-- === FOREIGN KEYS ===
ALTER TABLE [dbo].[Offer] ADD CONSTRAINT [FK_Offer_Customer_CustomerId] FOREIGN KEY ([CustomerId]) REFERENCES [dbo].[Customer] ([Id]);
ALTER TABLE [dbo].[Offer] ADD CONSTRAINT [FK_Offer_ReferenceData_BookTypeId] FOREIGN KEY ([BookTypeId]) REFERENCES [dbo].[ReferenceData] ([Id]);
ALTER TABLE [dbo].[Offer] ADD CONSTRAINT [FK_Offer_ReferenceData_ConditionId] FOREIGN KEY ([ConditionId]) REFERENCES [dbo].[ReferenceData] ([Id]);
ALTER TABLE [dbo].[Offer] ADD CONSTRAINT [FK_Offer_ReferenceData_GenreId] FOREIGN KEY ([GenreId]) REFERENCES [dbo].[ReferenceData] ([Id]);
ALTER TABLE [dbo].[Offer] ADD CONSTRAINT [FK_Offer_ReferenceData_PublisherId] FOREIGN KEY ([PublisherId]) REFERENCES [dbo].[ReferenceData] ([Id]);
