CREATE TABLE [HumanResources].[Employee](
[BusinessEntityID] int NOT NULL,
[NationalIDNumber] nvarchar(15) COLLATE SQL_Latin1_General_CP1_CI_AS NOT NULL,
[LoginID] nvarchar(256) COLLATE SQL_Latin1_General_CP1_CI_AS NOT NULL,
[OrganizationNode] hierarchyid NULL,
[OrganizationLevel] AS ([OrganizationNode].[GetLevel]()),
[JobTitle] nvarchar(50) COLLATE SQL_Latin1_General_CP1_CI_AS NOT NULL,
[BirthDate] date NOT NULL,
[MaritalStatus] nchar(1) COLLATE SQL_Latin1_General_CP1_CI_AS NOT NULL,
[Gender] nchar(1) COLLATE SQL_Latin1_General_CP1_CI_AS NOT NULL,
[HireDate] date NOT NULL,
[SalariedFlag] Flag NOT NULL DEFAULT ((1)),
[VacationHours] smallint NOT NULL DEFAULT ((0)),
[SickLeaveHours] smallint NOT NULL DEFAULT ((0)),
[CurrentFlag] Flag NOT NULL DEFAULT ((1)),
[rowguid] uniqueidentifier ROWGUIDCOL NOT NULL DEFAULT (newid()),
[ModifiedDate] datetime NOT NULL DEFAULT (getdate())
)
ON [PRIMARY];