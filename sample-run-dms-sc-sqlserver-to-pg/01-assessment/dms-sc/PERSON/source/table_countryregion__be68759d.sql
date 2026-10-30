CREATE TABLE [Person].[CountryRegion](
[CountryRegionCode] nvarchar(3) COLLATE SQL_Latin1_General_CP1_CI_AS NOT NULL,
[Name] Name NOT NULL,
[ModifiedDate] datetime NOT NULL DEFAULT (getdate())
)
ON [PRIMARY];