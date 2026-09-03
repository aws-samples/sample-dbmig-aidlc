CREATE TABLE [HumanResources].[EmployeeDepartmentHistory](
[BusinessEntityID] int NOT NULL,
[DepartmentID] smallint NOT NULL,
[ShiftID] tinyint NOT NULL,
[StartDate] date NOT NULL,
[EndDate] date NULL,
[ModifiedDate] datetime NOT NULL DEFAULT (getdate())
)
ON [PRIMARY];