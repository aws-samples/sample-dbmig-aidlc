ALTER TABLE [Person].[StateProvince]
ADD CONSTRAINT [FK_StateProvince_SalesTerritory_TerritoryID] FOREIGN KEY ([TerritoryID]) 
REFERENCES [Sales].[SalesTerritory] ([TerritoryID]);