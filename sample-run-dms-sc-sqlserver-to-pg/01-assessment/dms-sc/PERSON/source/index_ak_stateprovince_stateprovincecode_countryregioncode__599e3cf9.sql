CREATE UNIQUE NONCLUSTERED INDEX [AK_StateProvince_StateProvinceCode_CountryRegionCode]
    ON [Person].[StateProvince] ([StateProvinceCode] ASC, [CountryRegionCode] ASC);