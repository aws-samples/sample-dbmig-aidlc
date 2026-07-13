-- HumanResources.vJobCandidateEmployment -> humanresources.vjobcandidateemployment
CREATE VIEW humanresources.vjobcandidateemployment AS
SELECT
    jc.jobcandidateid,
    NULLIF(replace((xpath('r:Emp.StartDate/text()', emp.node, n.ns))[1]::text, 'Z', ''), '')::timestamp AS "Emp.StartDate",
    NULLIF(replace((xpath('r:Emp.EndDate/text()',   emp.node, n.ns))[1]::text, 'Z', ''), '')::timestamp AS "Emp.EndDate",
    (xpath('r:Emp.OrgName/text()',  emp.node, n.ns))[1]::text AS "Emp.OrgName",
    (xpath('r:Emp.JobTitle/text()', emp.node, n.ns))[1]::text AS "Emp.JobTitle",
    (xpath('r:Emp.Responsibility/text()',   emp.node, n.ns))[1]::text AS "Emp.Responsibility",
    (xpath('r:Emp.FunctionCategory/text()', emp.node, n.ns))[1]::text AS "Emp.FunctionCategory",
    (xpath('r:Emp.IndustryCategory/text()', emp.node, n.ns))[1]::text AS "Emp.IndustryCategory",
    (xpath('r:Emp.Location/r:Location/r:Loc.CountryRegion/text()', emp.node, n.ns))[1]::text AS "Emp.Loc.CountryRegion",
    (xpath('r:Emp.Location/r:Location/r:Loc.State/text()', emp.node, n.ns))[1]::text AS "Emp.Loc.State",
    (xpath('r:Emp.Location/r:Location/r:Loc.City/text()',  emp.node, n.ns))[1]::text AS "Emp.Loc.City"
FROM humanresources.jobcandidate jc
CROSS JOIN LATERAL (SELECT ARRAY[ARRAY['r','http://schemas.microsoft.com/sqlserver/2004/07/adventure-works/Resume']] AS ns) n
CROSS JOIN LATERAL unnest(xpath('/r:Resume/r:Employment', jc.resume, n.ns)) AS emp(node);
