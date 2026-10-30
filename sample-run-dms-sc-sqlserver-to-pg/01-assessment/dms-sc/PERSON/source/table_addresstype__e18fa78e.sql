CREATE TABLE [Person].[AddressType](
[AddressTypeID] int IDENTITY(1, 1) NOT NULL,
[Name] Name NOT NULL,
[rowguid] uniqueidentifier ROWGUIDCOL NOT NULL DEFAULT (newid()),
[ModifiedDate] datetime NOT NULL DEFAULT (getdate())
)
ON [PRIMARY];