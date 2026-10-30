ALTER TABLE [HumanResources].[Employee]
ADD CONSTRAINT [CK_Employee_VacationHours] CHECK (([VacationHours]>=(-40) AND [VacationHours]<=(240)));