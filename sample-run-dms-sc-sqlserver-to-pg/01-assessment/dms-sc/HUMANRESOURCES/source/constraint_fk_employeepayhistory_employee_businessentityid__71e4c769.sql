ALTER TABLE [HumanResources].[EmployeePayHistory]
ADD CONSTRAINT [FK_EmployeePayHistory_Employee_BusinessEntityID] FOREIGN KEY ([BusinessEntityID]) 
REFERENCES [HumanResources].[Employee] ([BusinessEntityID]);