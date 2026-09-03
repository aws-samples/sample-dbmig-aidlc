CREATE NONCLUSTERED INDEX [IX_Employee_OrganizationLevel_OrganizationNode]
    ON [HumanResources].[Employee] ([OrganizationLevel] ASC, [OrganizationNode] ASC);