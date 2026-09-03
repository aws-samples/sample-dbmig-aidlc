ALTER TABLE [Person].[PersonPhone]
ADD CONSTRAINT [FK_PersonPhone_Person_BusinessEntityID] FOREIGN KEY ([BusinessEntityID]) 
REFERENCES [Person].[Person] ([BusinessEntityID]);