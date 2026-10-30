CREATE OR REPLACE PROCEDURE adventureworks_humanresources.uspupdateemployeehireinfo(IN par_businessentityid INTEGER, IN par_jobtitle VARCHAR, IN par_hiredate TIMESTAMP WITHOUT TIME ZONE, IN par_ratechangedate TIMESTAMP WITHOUT TIME ZONE, IN par_rate NUMERIC, IN par_payfrequency SMALLINT, IN par_currentflag adventureworks_dbo.flag)
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
        [7807 - Severity CRITICAL - PostgreSQL does not support explicit transaction management commands such as BEGIN TRAN, SAVE TRAN in functions. Convert your source code manually.]
        BEGIN TRANSACTION;
        */
        UPDATE adventureworks_humanresources.employee
        SET jobtitle = par_JobTitle, hiredate = par_HireDate, currentflag = par_CurrentFlag
            WHERE businessentityid = par_BusinessEntityID;
        INSERT INTO adventureworks_humanresources.employeepayhistory (businessentityid, ratechangedate, rate, payfrequency)
        VALUES (par_BusinessEntityID, par_RateChangeDate, par_Rate, par_PayFrequency);
        /*
        [7615 - Severity CRITICAL - Your code ends a transaction inside a block with exception handlers. Revise your code to move transaction control to the application side and try again.]
        COMMIT TRANSACTION;
        */
        EXCEPTION
            WHEN OTHERS THEN
                /* Rollback any active or uncommittable transactions before */
                /* inserting information in the ErrorLog */
                
                /*
                [7811 - Severity CRITICAL - PostgreSQL doesn't support the @@TRANCOUNT function. DMS SC skips this unsupported function in the converted code. Create a user-defined function to replace the unsupported function., 7807 - Severity CRITICAL - PostgreSQL does not support explicit transaction management commands such as BEGIN TRAN, SAVE TRAN in functions. Convert your source code manually.]
                IF @@TRANCOUNT > 0
                        BEGIN
                            ROLLBACK TRANSACTION;
                        END
                */
                CALL adventureworks_dbo.usplogerror(par_ErrorLogID => usplogerror$par_ErrorLogID, return_code => usplogerror$ReturnCode);
    END;
END;
$BODY$
LANGUAGE plpgsql;