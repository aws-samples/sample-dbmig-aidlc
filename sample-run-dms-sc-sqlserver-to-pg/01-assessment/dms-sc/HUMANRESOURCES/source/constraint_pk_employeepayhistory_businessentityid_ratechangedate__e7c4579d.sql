ALTER TABLE [HumanResources].[EmployeePayHistory]
ADD CONSTRAINT [PK_EmployeePayHistory_BusinessEntityID_RateChangeDate] PRIMARY KEY CLUSTERED ([BusinessEntityID], [RateChangeDate]);