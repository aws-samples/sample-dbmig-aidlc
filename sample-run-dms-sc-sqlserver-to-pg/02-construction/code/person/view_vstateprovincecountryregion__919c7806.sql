CREATE OR REPLACE  VIEW person.vstateprovincecountryregion (stateprovinceid, stateprovincecode, isonlystateprovinceflag, stateprovincename, territoryid, countryregioncode, countryregionname) AS
SELECT
    sp.stateprovinceid, sp.stateprovincecode, sp.isonlystateprovinceflag, sp.name AS stateprovincename, sp.territoryid, cr.countryregioncode, cr.name AS countryregionname
    FROM person.stateprovince AS sp
    INNER JOIN person.countryregion AS cr
        ON LOWER(sp.countryregioncode) = LOWER(cr.countryregioncode);