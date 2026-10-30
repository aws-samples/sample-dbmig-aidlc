-- MANUAL reconversion of HumanResources.uspUpdateEmployeePersonalInfo (7644).
-- EXECUTE AS CALLER dropped: PG procedures are SECURITY INVOKER by default (same effect).
-- The handler passes SQLSTATE/SQLERRM to the reconverted dbo.usplogerror (see its file).
CREATE OR REPLACE PROCEDURE adventureworks_humanresources.uspupdateemployeepersonalinfo(IN par_businessentityid integer, IN par_nationalidnumber character varying, IN par_birthdate timestamp without time zone, IN par_maritalstatus character, IN par_gender character)
 LANGUAGE plpgsql
AS $procedure$
DECLARE
    usplogerror$par_ErrorLogID INTEGER;
    usplogerror$ReturnCode INTEGER;
BEGIN
    UPDATE adventureworks_humanresources.employee
       SET nationalidnumber = par_nationalidnumber, birthdate = par_birthdate,
           maritalstatus = par_maritalstatus, gender = par_gender
     WHERE businessentityid = par_businessentityid;
EXCEPTION
    WHEN OTHERS THEN
        CALL adventureworks_dbo.usplogerror(par_errorlogid => usplogerror$par_ErrorLogID, return_code => usplogerror$ReturnCode,
                                              par_sqlstate => SQLSTATE, par_message => SQLERRM, par_procedure => 'uspupdateemployeepersonalinfo');
END;
$procedure$;
