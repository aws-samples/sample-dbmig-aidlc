CREATE TABLE [HumanResources].[Department](
[DepartmentID] smallint IDENTITY(1, 1) NOT NULL,
[Name] Name NOT NULL,
[GroupName] Name NOT NULL,
[ModifiedDate] datetime NOT NULL DEFAULT (getdate())
)
ON [PRIMARY];