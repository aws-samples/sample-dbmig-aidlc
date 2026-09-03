CREATE TABLE [Person].[BusinessEntityAddress](
[BusinessEntityID] int NOT NULL,
[AddressID] int NOT NULL,
[AddressTypeID] int NOT NULL,
[rowguid] uniqueidentifier ROWGUIDCOL NOT NULL DEFAULT (newid()),
[ModifiedDate] datetime NOT NULL DEFAULT (getdate())
)
ON [PRIMARY];