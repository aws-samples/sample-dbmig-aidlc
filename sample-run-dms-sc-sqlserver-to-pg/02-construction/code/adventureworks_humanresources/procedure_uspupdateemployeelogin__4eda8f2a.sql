-- MANUAL reconversion of HumanResources.uspUpdateEmployeeLogin (7644, 7657, 7706).
-- DMS SC commented the UPDATE out (hierarchyid parameter, 7657) and left an EMPTY body, so the
-- converted procedure silently did nothing. The UPDATE is restored with organizationnode as
-- varchar (the hierarchyid string form '/1/2/', matching how the column was converted).
-- The handler passes SQLSTATE/SQLERRM to the reconverted dbo.usplogerror (see its file).
CREATE OR REPLACE PROCEDURE adventureworks_humanresources.uspupdateemployeelogin(IN par_businessentityid integer, IN par_organizationnode character varying, IN par_loginid character varying, IN par_jobtitle character varying, IN par_hiredate timestamp without time zone, IN par_currentflag adventureworks_dbo.flag)
 LANGUAGE plpgsql
AS $procedure$
DECLARE
    usplogerror$par_ErrorLogID INTEGER;
    usplogerror$ReturnCode INTEGER;
BEGIN
    UPDATE adventureworks_humanresources.employee
       SET organizationnode = par_organizationnode, loginid = par_loginid, jobtitle = par_jobtitle,
           hiredate = par_hiredate, currentflag = par_currentflag
     WHERE businessentityid = par_businessentityid;
EXCEPTION
    WHEN OTHERS THEN
        CALL adventureworks_dbo.usplogerror(par_errorlogid => usplogerror$par_ErrorLogID, return_code => usplogerror$ReturnCode,
                                              par_sqlstate => SQLSTATE, par_message => SQLERRM, par_procedure => 'uspupdateemployeelogin');
END;
$procedure$;
