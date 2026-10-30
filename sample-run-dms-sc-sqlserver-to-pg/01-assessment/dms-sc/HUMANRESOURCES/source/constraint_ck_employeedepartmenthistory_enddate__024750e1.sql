ALTER TABLE [HumanResources].[EmployeeDepartmentHistory]
ADD CONSTRAINT [CK_EmployeeDepartmentHistory_EndDate] CHECK (([EndDate]>=[StartDate] OR [EndDate] IS NULL));