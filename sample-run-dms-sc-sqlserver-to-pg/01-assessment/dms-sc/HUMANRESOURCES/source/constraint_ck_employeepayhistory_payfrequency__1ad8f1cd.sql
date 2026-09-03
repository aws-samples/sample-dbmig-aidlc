ALTER TABLE [HumanResources].[EmployeePayHistory]
ADD CONSTRAINT [CK_EmployeePayHistory_PayFrequency] CHECK (([PayFrequency]=(2) OR [PayFrequency]=(1)));