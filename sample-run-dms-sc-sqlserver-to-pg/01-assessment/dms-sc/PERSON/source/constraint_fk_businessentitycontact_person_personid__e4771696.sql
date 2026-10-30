ALTER TABLE [Person].[BusinessEntityContact]
ADD CONSTRAINT [FK_BusinessEntityContact_Person_PersonID] FOREIGN KEY ([PersonID]) 
REFERENCES [Person].[Person] ([BusinessEntityID]);