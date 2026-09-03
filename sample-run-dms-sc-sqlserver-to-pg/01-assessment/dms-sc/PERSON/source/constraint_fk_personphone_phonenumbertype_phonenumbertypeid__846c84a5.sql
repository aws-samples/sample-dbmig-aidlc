ALTER TABLE [Person].[PersonPhone]
ADD CONSTRAINT [FK_PersonPhone_PhoneNumberType_PhoneNumberTypeID] FOREIGN KEY ([PhoneNumberTypeID]) 
REFERENCES [Person].[PhoneNumberType] ([PhoneNumberTypeID]);