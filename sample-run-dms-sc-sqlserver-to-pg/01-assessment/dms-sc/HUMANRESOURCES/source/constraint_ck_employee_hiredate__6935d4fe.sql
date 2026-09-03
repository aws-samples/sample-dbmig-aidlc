ALTER TABLE [HumanResources].[Employee]
ADD CONSTRAINT [CK_Employee_HireDate] CHECK (([HireDate]>='1996-07-01' AND [HireDate]<=dateadd(day,(1),getdate())));