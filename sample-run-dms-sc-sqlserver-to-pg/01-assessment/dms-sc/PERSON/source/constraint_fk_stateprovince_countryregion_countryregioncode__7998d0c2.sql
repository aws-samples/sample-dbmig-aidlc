ALTER TABLE [Person].[StateProvince]
ADD CONSTRAINT [FK_StateProvince_CountryRegion_CountryRegionCode] FOREIGN KEY ([CountryRegionCode]) 
REFERENCES [Person].[CountryRegion] ([CountryRegionCode]);