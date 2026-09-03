CREATE OR REPLACE  VIEW humanresources.vemployeedepartment (businessentityid, title, firstname, middlename, lastname, suffix, jobtitle, department, groupname, startdate) AS
SELECT
    e.businessentityid, p.title, p.firstname, p.middlename, p.lastname, p.suffix, e.jobtitle, d.name AS department, d.groupname, edh.startdate
    FROM humanresources.employee AS e
    INNER JOIN person.person AS p
        ON p.businessentityid = e.businessentityid
    INNER JOIN humanresources.employeedepartmenthistory AS edh
        ON e.businessentityid = edh.businessentityid
    INNER JOIN humanresources.department AS d
        ON edh.departmentid = d.departmentid
    WHERE edh.enddate IS NULL;