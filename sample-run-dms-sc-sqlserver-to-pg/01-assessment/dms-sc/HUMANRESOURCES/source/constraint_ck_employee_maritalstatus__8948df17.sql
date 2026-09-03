ALTER TABLE [HumanResources].[Employee]
ADD CONSTRAINT [CK_Employee_MaritalStatus] CHECK ((upper([MaritalStatus])='S' OR upper([MaritalStatus])='M'));