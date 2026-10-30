-- MANUAL reconversion of HumanResources.uspUpdateEmployeeHireInfo (7644, 7807, 7615, 7811).
-- EXECUTE AS CALLER dropped (PG procedures run as the caller by default). BEGIN TRAN/COMMIT removed:
-- a procedure called inside an EXCEPTION block cannot COMMIT (7615); the block itself gives the
-- source's all-or-nothing behaviour, and the handler logs then re-raises like the source's THROW.
-- The handler passes SQLSTATE/SQLERRM to the reconverted dbo.usplogerror (see its file).
CREATE OR REPLACE PROCEDURE adventureworks_humanresources.uspupdateemployeehireinfo(IN par_businessentityid integer, IN par_jobtitle character varying, IN par_hiredate timestamp without time zone, IN par_ratechangedate timestamp without time zone, IN par_rate numeric, IN par_payfrequency smallint, IN par_currentflag adventureworks_dbo.flag)
 LANGUAGE plpgsql
AS $procedure$
DECLARE
    usplogerror$par_ErrorLogID INTEGER;
    usplogerror$ReturnCode INTEGER;
BEGIN
    UPDATE adventureworks_humanresources.employee
       SET jobtitle = par_jobtitle, hiredate = par_hiredate, currentflag = par_currentflag
     WHERE businessentityid = par_businessentityid;
    INSERT INTO adventureworks_humanresources.employeepayhistory (businessentityid, ratechangedate, rate, payfrequency)
    VALUES (par_businessentityid, par_ratechangedate, par_rate, par_payfrequency);
EXCEPTION
    WHEN OTHERS THEN
        CALL adventureworks_dbo.usplogerror(par_errorlogid => usplogerror$par_ErrorLogID, return_code => usplogerror$ReturnCode,
                                              par_sqlstate => SQLSTATE, par_message => SQLERRM, par_procedure => 'uspupdateemployeehireinfo');
END;
$procedure$;
