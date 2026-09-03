CREATE TABLE [HumanResources].[EmployeePayHistory](
[BusinessEntityID] int NOT NULL,
[RateChangeDate] datetime NOT NULL,
[Rate] money NOT NULL,
[PayFrequency] tinyint NOT NULL,
[ModifiedDate] datetime NOT NULL DEFAULT (getdate())
)
ON [PRIMARY];