-- HumanResources.vJobCandidateEducation -> humanresources.vjobcandidateeducation
-- CROSS APPLY Resume.nodes('/Resume/Education') (many rows) -> LATERAL unnest(xpath(...)) over each Education node.
-- CONVERT(datetime, REPLACE(x,'Z',''),101) -> replace 'Z' then cast to timestamp.
CREATE VIEW humanresources.vjobcandidateeducation AS
SELECT
    jc.jobcandidateid,
    (xpath('r:Edu.Level/text()', edu.node, n.ns))[1]::text AS "Edu.Level",
    NULLIF(replace((xpath('r:Edu.StartDate/text()', edu.node, n.ns))[1]::text, 'Z', ''), '')::timestamp AS "Edu.StartDate",
    NULLIF(replace((xpath('r:Edu.EndDate/text()',   edu.node, n.ns))[1]::text, 'Z', ''), '')::timestamp AS "Edu.EndDate",
    (xpath('r:Edu.Degree/text()', edu.node, n.ns))[1]::text AS "Edu.Degree",
    (xpath('r:Edu.Major/text()',  edu.node, n.ns))[1]::text AS "Edu.Major",
    (xpath('r:Edu.Minor/text()',  edu.node, n.ns))[1]::text AS "Edu.Minor",
    (xpath('r:Edu.GPA/text()',    edu.node, n.ns))[1]::text AS "Edu.GPA",
    (xpath('r:Edu.GPAScale/text()', edu.node, n.ns))[1]::text AS "Edu.GPAScale",
    (xpath('r:Edu.School/text()', edu.node, n.ns))[1]::text AS "Edu.School",
    (xpath('r:Edu.Location/r:Location/r:Loc.CountryRegion/text()', edu.node, n.ns))[1]::text AS "Edu.Loc.CountryRegion",
    (xpath('r:Edu.Location/r:Location/r:Loc.State/text()', edu.node, n.ns))[1]::text AS "Edu.Loc.State",
    (xpath('r:Edu.Location/r:Location/r:Loc.City/text()',  edu.node, n.ns))[1]::text AS "Edu.Loc.City"
FROM humanresources.jobcandidate jc
CROSS JOIN LATERAL (SELECT ARRAY[ARRAY['r','http://schemas.microsoft.com/sqlserver/2004/07/adventure-works/Resume']] AS ns) n
CROSS JOIN LATERAL unnest(xpath('/r:Resume/r:Education', jc.resume, n.ns)) AS edu(node);
