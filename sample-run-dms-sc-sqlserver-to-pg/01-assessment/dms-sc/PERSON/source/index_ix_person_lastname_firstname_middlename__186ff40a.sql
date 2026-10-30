CREATE NONCLUSTERED INDEX [IX_Person_LastName_FirstName_MiddleName]
    ON [Person].[Person] ([LastName] ASC, [FirstName] ASC, [MiddleName] ASC);