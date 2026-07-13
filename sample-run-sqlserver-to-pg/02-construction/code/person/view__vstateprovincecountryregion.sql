-- Person.vStateProvinceCountryRegion -> person.vstateprovincecountryregion  (WITH SCHEMABINDING dropped)
CREATE VIEW person.vstateprovincecountryregion AS
SELECT sp.stateprovinceid,
       sp.stateprovincecode,
       sp.isonlystateprovinceflag,
       sp.name AS stateprovincename,
       sp.territoryid,
       cr.countryregioncode,
       cr.name AS countryregionname
FROM person.stateprovince sp
JOIN person.countryregion cr ON sp.countryregioncode = cr.countryregioncode;
