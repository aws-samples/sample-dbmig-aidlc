ALTER TABLE [Person].[PersonPhone]
ADD CONSTRAINT [PK_PersonPhone_BusinessEntityID_PhoneNumber_PhoneNumberTypeID] PRIMARY KEY CLUSTERED ([BusinessEntityID], [PhoneNumber], [PhoneNumberTypeID]);