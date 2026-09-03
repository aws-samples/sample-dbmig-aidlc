CREATE TABLE [Person].[ContactType](
[ContactTypeID] int IDENTITY(1, 1) NOT NULL,
[Name] Name NOT NULL,
[ModifiedDate] datetime NOT NULL DEFAULT (getdate())
)
ON [PRIMARY];