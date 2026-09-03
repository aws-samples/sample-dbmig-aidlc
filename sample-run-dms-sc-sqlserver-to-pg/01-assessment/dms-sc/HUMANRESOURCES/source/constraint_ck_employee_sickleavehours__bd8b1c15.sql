ALTER TABLE [HumanResources].[Employee]
ADD CONSTRAINT [CK_Employee_SickLeaveHours] CHECK (([SickLeaveHours]>=(0) AND [SickLeaveHours]<=(120)));