ALTER TABLE [Person].[Person]
ADD CONSTRAINT [FK_Person_BusinessEntity_BusinessEntityID] FOREIGN KEY ([BusinessEntityID]) 
REFERENCES [Person].[BusinessEntity] ([BusinessEntityID]);