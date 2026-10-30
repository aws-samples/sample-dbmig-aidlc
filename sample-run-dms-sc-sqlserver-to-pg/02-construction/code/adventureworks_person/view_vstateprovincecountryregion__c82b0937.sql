CREATE OR REPLACE  VIEW adventureworks_person.vstateprovincecountryregion (stateprovinceid, stateprovincecode, isonlystateprovinceflag, stateprovincename, territoryid, countryregioncode, countryregionname) AS
SELECT
    sp.stateprovinceid, sp.stateprovincecode, sp.isonlystateprovinceflag, sp.name AS stateprovincename, sp.territoryid, cr.countryregioncode, cr.name AS countryregionname
    FROM adventureworks_person.stateprovince AS sp
    INNER JOIN adventureworks_person.countryregion AS cr
        ON LOWER(sp.countryregioncode) = LOWER(cr.countryregioncode);