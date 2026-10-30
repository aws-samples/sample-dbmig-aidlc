CREATE TABLE [Person].[PhoneNumberType](
[PhoneNumberTypeID] int IDENTITY(1, 1) NOT NULL,
[Name] Name NOT NULL,
[ModifiedDate] datetime NOT NULL DEFAULT (getdate())
)
ON [PRIMARY];