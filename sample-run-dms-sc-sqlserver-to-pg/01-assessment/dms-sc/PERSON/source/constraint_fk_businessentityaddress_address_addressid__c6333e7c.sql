ALTER TABLE [Person].[BusinessEntityAddress]
ADD CONSTRAINT [FK_BusinessEntityAddress_Address_AddressID] FOREIGN KEY ([AddressID]) 
REFERENCES [Person].[Address] ([AddressID]);