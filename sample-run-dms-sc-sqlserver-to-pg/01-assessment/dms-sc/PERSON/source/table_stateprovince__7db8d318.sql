CREATE TABLE [Person].[StateProvince](
[StateProvinceID] int IDENTITY(1, 1) NOT NULL,
[StateProvinceCode] nchar(3) COLLATE SQL_Latin1_General_CP1_CI_AS NOT NULL,
[CountryRegionCode] nvarchar(3) COLLATE SQL_Latin1_General_CP1_CI_AS NOT NULL,
[IsOnlyStateProvinceFlag] Flag NOT NULL DEFAULT ((1)),
[Name] Name NOT NULL,
[TerritoryID] int NOT NULL,
[rowguid] uniqueidentifier ROWGUIDCOL NOT NULL DEFAULT (newid()),
[ModifiedDate] datetime NOT NULL DEFAULT (getdate())
)
ON [PRIMARY];