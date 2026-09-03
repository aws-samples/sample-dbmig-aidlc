ALTER TABLE [HumanResources].[EmployeeDepartmentHistory]
ADD CONSTRAINT [FK_EmployeeDepartmentHistory_Shift_ShiftID] FOREIGN KEY ([ShiftID]) 
REFERENCES [HumanResources].[Shift] ([ShiftID]);