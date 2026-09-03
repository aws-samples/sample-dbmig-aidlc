CREATE TABLE [Person].[Address](
[AddressID] int IDENTITY(1, 1) NOT NULL,
[AddressLine1] nvarchar(60) COLLATE SQL_Latin1_General_CP1_CI_AS NOT NULL,
[AddressLine2] nvarchar(60) COLLATE SQL_Latin1_General_CP1_CI_AS NULL,
[City] nvarchar(30) COLLATE SQL_Latin1_General_CP1_CI_AS NOT NULL,
[StateProvinceID] int NOT NULL,
[PostalCode] nvarchar(15) COLLATE SQL_Latin1_General_CP1_CI_AS NOT NULL,
[SpatialLocation] geography NULL,
[rowguid] uniqueidentifier ROWGUIDCOL NOT NULL DEFAULT (newid()),
[ModifiedDate] datetime NOT NULL DEFAULT (getdate())
)
ON [PRIMARY];