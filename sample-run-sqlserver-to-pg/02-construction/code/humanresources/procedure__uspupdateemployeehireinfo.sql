-- HumanResources.uspUpdateEmployeeHireInfo -> humanresources.uspupdateemployeehireinfo
-- T-SQL TRY/CATCH -> PL/pgSQL EXCEPTION; money -> numeric; dbo.Flag -> boolean.
-- dbo.uspLogError (out of scope) is replaced by RAISE (re-raise the original error).
-- Explicit BEGIN TRANSACTION/COMMIT dropped: the caller controls the transaction.
CREATE OR REPLACE PROCEDURE humanresources.uspupdateemployeehireinfo(
    p_businessentityid integer,
    p_jobtitle         varchar,
    p_hiredate         timestamp,
    p_ratechangedate   timestamp,
    p_rate             numeric,
    p_payfrequency     smallint,
    p_currentflag      boolean)
AS $$
BEGIN
  UPDATE humanresources.employee
     SET jobtitle = p_jobtitle,
         hiredate = p_hiredate,
         currentflag = p_currentflag
   WHERE businessentityid = p_businessentityid;

  INSERT INTO humanresources.employeepayhistory
      (businessentityid, ratechangedate, rate, payfrequency)
  VALUES (p_businessentityid, p_ratechangedate, p_rate, p_payfrequency);
EXCEPTION WHEN OTHERS THEN
  -- Source swallows the error and logs it via dbo.uspLogError; mimic "log and continue"
  -- (the failed statements are rolled back to this block's implicit savepoint).
  RAISE WARNING 'uspUpdateEmployee error: %', SQLERRM;
END;
$$ LANGUAGE plpgsql;
