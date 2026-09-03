CREATE TABLE [Person].[BusinessEntity](
[BusinessEntityID] int IDENTITY(1, 1) NOT NULL,
[rowguid] uniqueidentifier ROWGUIDCOL NOT NULL DEFAULT (newid()),
[ModifiedDate] datetime NOT NULL DEFAULT (getdate())
)
ON [PRIMARY];