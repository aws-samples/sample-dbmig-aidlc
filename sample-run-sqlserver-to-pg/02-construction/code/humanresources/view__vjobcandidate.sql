-- HumanResources.vJobCandidate -> humanresources.vjobcandidate
-- Resume default-namespace XML shredded via xpath() (prefix 'r'). Dotted element names (Name.First,
-- Addr.Type, Loc.City ...) are preserved as quoted output columns to match the source view contract.
CREATE VIEW humanresources.vjobcandidate AS
SELECT
    jc.jobcandidateid, jc.businessentityid,
    (xpath('/r:Resume/r:Name/r:Name.Prefix/text()', jc.resume, n.ns))[1]::text AS "Name.Prefix",
    (xpath('/r:Resume/r:Name/r:Name.First/text()',  jc.resume, n.ns))[1]::text AS "Name.First",
    (xpath('/r:Resume/r:Name/r:Name.Middle/text()', jc.resume, n.ns))[1]::text AS "Name.Middle",
    (xpath('/r:Resume/r:Name/r:Name.Last/text()',   jc.resume, n.ns))[1]::text AS "Name.Last",
    (xpath('/r:Resume/r:Name/r:Name.Suffix/text()', jc.resume, n.ns))[1]::text AS "Name.Suffix",
    (xpath('/r:Resume/r:Skills/text()', jc.resume, n.ns))[1]::text AS "Skills",
    (xpath('/r:Resume/r:Address/r:Addr.Type/text()', jc.resume, n.ns))[1]::text AS "Addr.Type",
    (xpath('/r:Resume/r:Address/r:Addr.Location/r:Location/r:Loc.CountryRegion/text()', jc.resume, n.ns))[1]::text AS "Addr.Loc.CountryRegion",
    (xpath('/r:Resume/r:Address/r:Addr.Location/r:Location/r:Loc.State/text()', jc.resume, n.ns))[1]::text AS "Addr.Loc.State",
    (xpath('/r:Resume/r:Address/r:Addr.Location/r:Location/r:Loc.City/text()', jc.resume, n.ns))[1]::text AS "Addr.Loc.City",
    (xpath('/r:Resume/r:Address/r:Addr.PostalCode/text()', jc.resume, n.ns))[1]::text AS "Addr.PostalCode",
    (xpath('/r:Resume/r:EMail/text()', jc.resume, n.ns))[1]::text AS "EMail",
    (xpath('/r:Resume/r:WebSite/text()', jc.resume, n.ns))[1]::text AS "WebSite",
    jc.modifieddate
FROM humanresources.jobcandidate jc
CROSS JOIN LATERAL (SELECT ARRAY[ARRAY['r','http://schemas.microsoft.com/sqlserver/2004/07/adventure-works/Resume']] AS ns) n
WHERE jc.resume IS NOT NULL;
