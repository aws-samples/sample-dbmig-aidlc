CREATE OR REPLACE PROCEDURE adventureworks_humanresources.uspupdateemployeepersonalinfo(IN par_businessentityid INTEGER, IN par_nationalidnumber VARCHAR, IN par_birthdate TIMESTAMP WITHOUT TIME ZONE, IN par_maritalstatus CHAR, IN par_gender CHAR)
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
        UPDATE adventureworks_humanresources.employee
        SET nationalidnumber = par_NationalIDNumber, birthdate = par_BirthDate, maritalstatus = par_MaritalStatus, gender = par_Gender
            WHERE businessentityid = par_BusinessEntityID;
        EXCEPTION
            WHEN OTHERS THEN
                CALL adventureworks_dbo.usplogerror(par_ErrorLogID => usplogerror$par_ErrorLogID, return_code => usplogerror$ReturnCode);
    END;
END;
$BODY$
LANGUAGE plpgsql;