ALTER TABLE [Person].[Address]
ADD CONSTRAINT [FK_Address_StateProvince_StateProvinceID] FOREIGN KEY ([StateProvinceID]) 
REFERENCES [Person].[StateProvince] ([StateProvinceID]);