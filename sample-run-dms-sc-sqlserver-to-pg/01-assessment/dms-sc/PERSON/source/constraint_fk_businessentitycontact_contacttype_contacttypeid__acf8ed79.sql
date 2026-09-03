ALTER TABLE [Person].[BusinessEntityContact]
ADD CONSTRAINT [FK_BusinessEntityContact_ContactType_ContactTypeID] FOREIGN KEY ([ContactTypeID]) 
REFERENCES [Person].[ContactType] ([ContactTypeID]);