CREATE TABLE [Person].[BusinessEntityContact](
[BusinessEntityID] int NOT NULL,
[PersonID] int NOT NULL,
[ContactTypeID] int NOT NULL,
[rowguid] uniqueidentifier ROWGUIDCOL NOT NULL DEFAULT (newid()),
[ModifiedDate] datetime NOT NULL DEFAULT (getdate())
)
ON [PRIMARY];