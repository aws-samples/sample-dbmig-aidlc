CREATE OR REPLACE PROCEDURE adventureworks_humanresources.uspupdateemployeelogin(IN par_businessentityid INTEGER, IN par_organizationnode VARCHAR, IN par_loginid VARCHAR, IN par_jobtitle VARCHAR, IN par_hiredate TIMESTAMP WITHOUT TIME ZONE, IN par_currentflag adventureworks_dbo.flag)
AS 
$BODY$
DECLARE
    usplogerror$par_ErrorLogID INTEGER;
    usplogerror$ReturnCode INTEGER;
BEGIN
    /*
    [7644 - Severity CRITICAL - PostgreSQL doesn't support the EXECUTE AS CALLER clause. Convert your source code manually.]
    EXECUTE AS CALLER
    */
    BEGIN
        /*
        [7657 - Severity CRITICAL - PostgreSQL doesn't support the hierarchyid data type. Convert your source code manually to make sure that you store data of the hierarchyid data type using a compatible type in PostgreSQL or a composite type.]
        UPDATE [HumanResources].[Employee]
                SET [OrganizationNode] = @OrganizationNode
                    ,[LoginID] = @LoginID
                    ,[JobTitle] = @JobTitle
                    ,[HireDate] = @HireDate
                    ,[CurrentFlag] = @CurrentFlag
                WHERE [BusinessEntityID] = @BusinessEntityID;
        */
        BEGIN
        END;
        EXCEPTION
            WHEN OTHERS THEN
                CALL adventureworks_dbo.usplogerror(par_ErrorLogID => usplogerror$par_ErrorLogID, return_code => usplogerror$ReturnCode);
    END;
END;
$BODY$
LANGUAGE plpgsql;