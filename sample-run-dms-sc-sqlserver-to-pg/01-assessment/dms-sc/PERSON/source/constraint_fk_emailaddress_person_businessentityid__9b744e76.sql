ALTER TABLE [Person].[EmailAddress]
ADD CONSTRAINT [FK_EmailAddress_Person_BusinessEntityID] FOREIGN KEY ([BusinessEntityID]) 
REFERENCES [Person].[Person] ([BusinessEntityID]);