ALTER TABLE [Person].[BusinessEntityContact]
ADD CONSTRAINT [FK_BusinessEntityContact_BusinessEntity_BusinessEntityID] FOREIGN KEY ([BusinessEntityID]) 
REFERENCES [Person].[BusinessEntity] ([BusinessEntityID]);