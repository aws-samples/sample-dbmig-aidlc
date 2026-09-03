CREATE OR REPLACE FUNCTION person.fn_iuperson()
RETURNS trigger
AS
$BODY$
DECLARE
    var_Count INTEGER;
    update$BusinessEntityID BOOLEAN;
    update$Demographics BOOLEAN;
BEGIN
    /* CREATING TEMPORARY TABLES */
    IF (TG_OP = 'INSERT') THEN
        CREATE TEMPORARY TABLE IF NOT EXISTS deleted$dd8b1d18
        AS
        TABLE inserted$dd8b1d18
        WITH NO DATA;
    ELSIF (TG_OP = 'DELETE') THEN
        CREATE TEMPORARY TABLE IF NOT EXISTS inserted$dd8b1d18
        AS
        TABLE deleted$dd8b1d18
        WITH NO DATA;
    END IF;
    CASE TG_OP
        WHEN 'INSERT' THEN
            update$BusinessEntityID = TRUE;
        WHEN 'UPDATE' THEN
            update$BusinessEntityID = ((SELECT
                array_agg(BusinessEntityID)
                FROM deleted$dd8b1d18) != (SELECT
                array_agg(BusinessEntityID)
                FROM inserted$dd8b1d18));
        ELSE
            update$BusinessEntityID := FALSE;
    END CASE;
    CASE TG_OP
        WHEN 'INSERT' THEN
            update$Demographics = TRUE;
        WHEN 'UPDATE' THEN
            update$Demographics = ((SELECT
                array_agg(Demographics)
                FROM deleted$dd8b1d18) != (SELECT
                array_agg(Demographics)
                FROM inserted$dd8b1d18));
        ELSE
            update$Demographics := FALSE;
    END CASE;
    /*
    [7833 - Severity CRITICAL - DMS SC can't convert the @@rowcount function in the current context. Convert your source code manually.]
    SET @Count = @@ROWCOUNT;
    */
    IF var_Count = 0 THEN
        RETURN NULL;
    END IF;

    IF update$BusinessEntityID OR update$Demographics THEN
        UPDATE person.person
        SET Demographics = '<IndividualSurvey xmlns="http://schemas.microsoft.com/sqlserver/2004/07/adventure-works/IndividualSurvey"> 
            <TotalPurchaseYTD>0.00</TotalPurchaseYTD> 
            </IndividualSurvey>'
        FROM inserted$dd8b1d18
            WHERE person.person.Person.BusinessEntityID = inserted.businessentityid AND inserted.demographics IS NULL;
        /*
        [7708 - Severity CRITICAL - DMS SC can't convert the usage of the unsupported XML.MODIFY(VARCHAR) data type. Convert your source code manually., 7708 - Severity CRITICAL - DMS SC can't convert the usage of the unsupported XML.EXIST(VARCHAR) data type. Convert your source code manually.]
        UPDATE [Person].[Person]
                SET [Demographics].modify(N'declare default element namespace "http://schemas.microsoft.com/sqlserver/2004/07/adventure-works/IndividualSurvey";
                    insert <TotalPurchaseYTD>0.00</TotalPurchaseYTD>
                    as first
                    into (/IndividualSurvey)[1]')
                FROM inserted
                WHERE [Person].[Person].[BusinessEntityID] = inserted.[BusinessEntityID]
                    AND inserted.[Demographics] IS NOT NULL
                    AND inserted.[Demographics].exist(N'declare default element namespace
                        "http://schemas.microsoft.com/sqlserver/2004/07/adventure-works/IndividualSurvey";
                        /IndividualSurvey/TotalPurchaseYTD') <> 1;
        */
    END IF;
    RETURN NULL;
END;
$BODY$
LANGUAGE  plpgsql;