CREATE TABLE [Person].[PersonPhone](
[BusinessEntityID] int NOT NULL,
[PhoneNumber] Phone NOT NULL,
[PhoneNumberTypeID] int NOT NULL,
[ModifiedDate] datetime NOT NULL DEFAULT (getdate())
)
ON [PRIMARY];