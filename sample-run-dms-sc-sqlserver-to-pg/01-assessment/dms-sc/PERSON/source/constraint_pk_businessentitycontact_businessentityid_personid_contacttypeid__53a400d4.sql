ALTER TABLE [Person].[BusinessEntityContact]
ADD CONSTRAINT [PK_BusinessEntityContact_BusinessEntityID_PersonID_ContactTypeID] PRIMARY KEY CLUSTERED ([BusinessEntityID], [PersonID], [ContactTypeID]);