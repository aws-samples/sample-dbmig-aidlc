CREATE TABLE [Person].[EmailAddress](
[BusinessEntityID] int NOT NULL,
[EmailAddressID] int IDENTITY(1, 1) NOT NULL,
[EmailAddress] nvarchar(50) COLLATE SQL_Latin1_General_CP1_CI_AS NULL,
[rowguid] uniqueidentifier ROWGUIDCOL NOT NULL DEFAULT (newid()),
[ModifiedDate] datetime NOT NULL DEFAULT (getdate())
)
ON [PRIMARY];