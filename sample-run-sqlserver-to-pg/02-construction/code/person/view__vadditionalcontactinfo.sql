-- Person.vAdditionalContactInfo -> person.vadditionalcontactinfo
-- SQL Server XML .nodes()/.value() with ci/act namespaces -> PostgreSQL xpath() with a namespace map.
-- OUTER APPLY over the single AdditionalContactInfo root becomes a direct per-row extract (WHERE NOT NULL).
CREATE VIEW person.vadditionalcontactinfo AS
SELECT
    p.businessentityid, p.firstname, p.middlename, p.lastname,
    (xpath('/ci:AdditionalContactInfo/act:telephoneNumber[1]/act:number/text()', p.additionalcontactinfo, n.ns))[1]::text AS telephonenumber,
    btrim((xpath('/ci:AdditionalContactInfo/act:telephoneNumber[1]/act:SpecialInstructions/text()', p.additionalcontactinfo, n.ns))[1]::text) AS telephonespecialinstructions,
    (xpath('/ci:AdditionalContactInfo/act:homePostalAddress[1]/act:Street/text()', p.additionalcontactinfo, n.ns))[1]::text AS street,
    (xpath('/ci:AdditionalContactInfo/act:homePostalAddress[1]/act:City/text()', p.additionalcontactinfo, n.ns))[1]::text AS city,
    (xpath('/ci:AdditionalContactInfo/act:homePostalAddress[1]/act:StateProvince/text()', p.additionalcontactinfo, n.ns))[1]::text AS stateprovince,
    (xpath('/ci:AdditionalContactInfo/act:homePostalAddress[1]/act:PostalCode/text()', p.additionalcontactinfo, n.ns))[1]::text AS postalcode,
    (xpath('/ci:AdditionalContactInfo/act:homePostalAddress[1]/act:CountryRegion/text()', p.additionalcontactinfo, n.ns))[1]::text AS countryregion,
    (xpath('/ci:AdditionalContactInfo/act:homePostalAddress[1]/act:SpecialInstructions/text()', p.additionalcontactinfo, n.ns))[1]::text AS homeaddressspecialinstructions,
    (xpath('/ci:AdditionalContactInfo/act:eMail[1]/act:eMailAddress/text()', p.additionalcontactinfo, n.ns))[1]::text AS emailaddress,
    btrim((xpath('/ci:AdditionalContactInfo/act:eMail[1]/act:SpecialInstructions/text()', p.additionalcontactinfo, n.ns))[1]::text) AS emailspecialinstructions,
    (xpath('/ci:AdditionalContactInfo/act:eMail[1]/act:SpecialInstructions/act:telephoneNumber/act:number/text()', p.additionalcontactinfo, n.ns))[1]::text AS emailtelephonenumber,
    p.rowguid, p.modifieddate
FROM person.person p
CROSS JOIN LATERAL (SELECT ARRAY[
    ARRAY['ci','http://schemas.microsoft.com/sqlserver/2004/07/adventure-works/ContactInfo'],
    ARRAY['act','http://schemas.microsoft.com/sqlserver/2004/07/adventure-works/ContactTypes']] AS ns) n
WHERE p.additionalcontactinfo IS NOT NULL;
