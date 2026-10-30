ALTER TABLE [HumanResources].[Employee]
ADD CONSTRAINT [CK_Employee_Gender] CHECK ((upper([Gender])='F' OR upper([Gender])='M'));