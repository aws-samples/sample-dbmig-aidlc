ALTER TABLE [Person].[BusinessEntityAddress]
ADD CONSTRAINT [FK_BusinessEntityAddress_AddressType_AddressTypeID] FOREIGN KEY ([AddressTypeID]) 
REFERENCES [Person].[AddressType] ([AddressTypeID]);