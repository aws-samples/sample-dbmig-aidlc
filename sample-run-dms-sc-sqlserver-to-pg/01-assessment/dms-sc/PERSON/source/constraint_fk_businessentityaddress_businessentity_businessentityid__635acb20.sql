ALTER TABLE [Person].[BusinessEntityAddress]
ADD CONSTRAINT [FK_BusinessEntityAddress_BusinessEntity_BusinessEntityID] FOREIGN KEY ([BusinessEntityID]) 
REFERENCES [Person].[BusinessEntity] ([BusinessEntityID]);