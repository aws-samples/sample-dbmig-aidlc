ALTER TABLE [HumanResources].[EmployeeDepartmentHistory]
ADD CONSTRAINT [FK_EmployeeDepartmentHistory_Department_DepartmentID] FOREIGN KEY ([DepartmentID]) 
REFERENCES [HumanResources].[Department] ([DepartmentID]);