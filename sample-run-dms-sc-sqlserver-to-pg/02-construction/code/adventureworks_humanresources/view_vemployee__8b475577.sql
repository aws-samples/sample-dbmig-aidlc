CREATE OR REPLACE  VIEW adventureworks_humanresources.vemployee (businessentityid, title, firstname, middlename, lastname, suffix, jobtitle, phonenumber, phonenumbertype, emailaddress, emailpromotion, addressline1, addressline2, city, stateprovincename, postalcode, countryregionname, additionalcontactinfo) AS
SELECT
    e.businessentityid, p.title, p.firstname, p.middlename, p.lastname, p.suffix, e.jobtitle, pp.phonenumber, pnt.name AS phonenumbertype, ea.emailaddress, p.emailpromotion, a.addressline1, a.addressline2, a.city, sp.name AS stateprovincename, a.postalcode, cr.name AS countryregionname, p.additionalcontactinfo
    FROM adventureworks_humanresources.employee AS e
    INNER JOIN adventureworks_person.person AS p
        ON p.businessentityid = e.businessentityid
    INNER JOIN adventureworks_person.businessentityaddress AS bea
        ON bea.businessentityid = e.businessentityid
    INNER JOIN adventureworks_person.address AS a
        ON a.addressid = bea.addressid
    INNER JOIN adventureworks_person.stateprovince AS sp
        ON sp.stateprovinceid = a.stateprovinceid
    INNER JOIN adventureworks_person.countryregion AS cr
        ON LOWER(cr.countryregioncode) = LOWER(sp.countryregioncode)
    LEFT OUTER JOIN adventureworks_person.personphone AS pp
        ON pp.businessentityid = p.businessentityid
    LEFT OUTER JOIN adventureworks_person.phonenumbertype AS pnt
        ON pp.phonenumbertypeid = pnt.phonenumbertypeid
    LEFT OUTER JOIN adventureworks_person.emailaddress AS ea
        ON p.businessentityid = ea.businessentityid;