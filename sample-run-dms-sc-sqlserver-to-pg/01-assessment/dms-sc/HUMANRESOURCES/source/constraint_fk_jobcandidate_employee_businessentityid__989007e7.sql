ALTER TABLE [HumanResources].[JobCandidate]
ADD CONSTRAINT [FK_JobCandidate_Employee_BusinessEntityID] FOREIGN KEY ([BusinessEntityID]) 
REFERENCES [HumanResources].[Employee] ([BusinessEntityID]);