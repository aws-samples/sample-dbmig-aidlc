CREATE TABLE [Person].[Person](
[BusinessEntityID] int NOT NULL,
[PersonType] nchar(2) COLLATE SQL_Latin1_General_CP1_CI_AS NOT NULL,
[NameStyle] NameStyle NOT NULL DEFAULT ((0)),
[Title] nvarchar(8) COLLATE SQL_Latin1_General_CP1_CI_AS NULL,
[FirstName] Name NOT NULL,
[MiddleName] Name NULL,
[LastName] Name NOT NULL,
[Suffix] nvarchar(10) COLLATE SQL_Latin1_General_CP1_CI_AS NULL,
[EmailPromotion] int NOT NULL DEFAULT ((0)),
[AdditionalContactInfo] xml NULL,
[Demographics] xml NULL,
[rowguid] uniqueidentifier ROWGUIDCOL NOT NULL DEFAULT (newid()),
[ModifiedDate] datetime NOT NULL DEFAULT (getdate())
)
ON [PRIMARY];