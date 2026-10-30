CREATE OR REPLACE  VIEW adventureworks_humanresources.vemployeedepartmenthistory (businessentityid, title, firstname, middlename, lastname, suffix, shift, department, groupname, startdate, enddate) AS
SELECT
    e.businessentityid, p.title, p.firstname, p.middlename, p.lastname, p.suffix, s.name AS shift, d.name AS department, d.groupname, edh.startdate, edh.enddate
    FROM adventureworks_humanresources.employee AS e
    INNER JOIN adventureworks_person.person AS p
        ON p.businessentityid = e.businessentityid
    INNER JOIN adventureworks_humanresources.employeedepartmenthistory AS edh
        ON e.businessentityid = edh.businessentityid
    INNER JOIN adventureworks_humanresources.department AS d
        ON edh.departmentid = d.departmentid
    INNER JOIN adventureworks_humanresources.shift AS s
        ON s.shiftid = edh.shiftid;