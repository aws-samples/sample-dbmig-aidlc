ALTER TABLE [HumanResources].[EmployeePayHistory]
ADD CONSTRAINT [CK_EmployeePayHistory_Rate] CHECK (([Rate]>=(6.50) AND [Rate]<=(200.00)));