ALTER TABLE [HumanResources].[EmployeeDepartmentHistory]
ADD CONSTRAINT [FK_EmployeeDepartmentHistory_Employee_BusinessEntityID] FOREIGN KEY ([BusinessEntityID]) 
REFERENCES [HumanResources].[Employee] ([BusinessEntityID]);