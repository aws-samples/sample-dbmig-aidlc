CREATE OR REPLACE FUNCTION adventureworks_dbo.ufngetcontactinformation(IN par_personid INTEGER)
RETURNS TABLE (personid INTEGER, firstname VARCHAR, lastname VARCHAR, jobtitle VARCHAR, businessentitytype VARCHAR)
AS
$BODY$
/* Columns returned by the function */
/* Returns the first name, last name, job title and business entity type for the specified contact. */
/* Since a contact can serve multiple roles, more than one row may be returned. */
# variable_conflict use_column
BEGIN
    DROP TABLE IF EXISTS ufngetcontactinformation$tmptbl;
    CREATE TEMPORARY TABLE ufngetcontactinformation$tmptbl
    (
        /* Columns returned by the function */
        personid INTEGER NOT NULL,
        firstname VARCHAR(50) NULL,
        lastname VARCHAR(50) NULL,
        jobtitle VARCHAR(50) NULL,
        businessentitytype VARCHAR(50) NULL);

    IF par_PersonID IS NOT NULL THEN
        IF EXISTS (SELECT
            *
            FROM humanresources.employee AS e
            WHERE e.businessentityid = par_PersonID) THEN
            INSERT INTO ufngetcontactinformation$tmptbl
            SELECT
                par_PersonID, p.firstname, p.lastname, e.jobtitle, 'Employee'
                FROM humanresources.employee AS e
                INNER JOIN person.person AS p
                    ON p.businessentityid = e.businessentityid
                WHERE e.businessentityid = par_PersonID;
        END IF;

        IF EXISTS (SELECT
            *
            FROM adventureworks_purchasing.vendor AS v
            INNER JOIN person.businessentitycontact AS bec
                ON bec.businessentityid = v.businessentityid
            WHERE bec.personid = par_PersonID) THEN
            INSERT INTO ufngetcontactinformation$tmptbl
            SELECT
                par_PersonID, p.firstname, p.lastname, ct.name, 'Vendor Contact'
                FROM adventureworks_purchasing.vendor AS v
                INNER JOIN person.businessentitycontact AS bec
                    ON bec.businessentityid = v.businessentityid
                INNER JOIN person.contacttype AS ct
                    ON ct.contacttypeid = bec.contacttypeid
                INNER JOIN person.person AS p
                    ON p.businessentityid = bec.personid
                WHERE bec.personid = par_PersonID;
        END IF;

        IF EXISTS (SELECT
            *
            FROM adventureworks_sales.store AS s
            INNER JOIN person.businessentitycontact AS bec
                ON bec.businessentityid = s.businessentityid
            WHERE bec.personid = par_PersonID) THEN
            INSERT INTO ufngetcontactinformation$tmptbl
            SELECT
                par_PersonID, p.firstname, p.lastname, ct.name, 'Store Contact'
                FROM adventureworks_sales.store AS s
                INNER JOIN person.businessentitycontact AS bec
                    ON bec.businessentityid = s.businessentityid
                INNER JOIN person.contacttype AS ct
                    ON ct.contacttypeid = bec.contacttypeid
                INNER JOIN person.person AS p
                    ON p.businessentityid = bec.personid
                WHERE bec.personid = par_PersonID;
        END IF;

        IF EXISTS (SELECT
            *
            FROM person.person AS p
            INNER JOIN adventureworks_sales.customer AS c
                ON c.personid = p.businessentityid
            WHERE p.businessentityid = par_PersonID AND c.storeid IS NULL) THEN
            INSERT INTO ufngetcontactinformation$tmptbl
            SELECT
                par_PersonID, p.firstname, p.lastname, NULL, 'Consumer'
                FROM person.person AS p
                INNER JOIN adventureworks_sales.customer AS c
                    ON c.personid = p.businessentityid
                WHERE p.businessentityid = par_PersonID AND c.storeid IS NULL;
        END IF;
    END IF;
    RETURN QUERY
    SELECT
        *
        FROM ufngetcontactinformation$tmptbl;
    DROP TABLE IF EXISTS ufngetcontactinformation$tmptbl;
    RETURN;
END;
$BODY$
LANGUAGE  plpgsql;