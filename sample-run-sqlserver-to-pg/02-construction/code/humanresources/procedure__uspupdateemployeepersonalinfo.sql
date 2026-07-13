-- HumanResources.uspUpdateEmployeePersonalInfo -> humanresources.uspupdateemployeepersonalinfo
CREATE OR REPLACE PROCEDURE humanresources.uspupdateemployeepersonalinfo(
    p_businessentityid integer,
    p_nationalidnumber varchar,
    p_birthdate        timestamp,
    p_maritalstatus    char,
    p_gender           char)
AS $$
BEGIN
  UPDATE humanresources.employee
     SET nationalidnumber = p_nationalidnumber,
         birthdate = p_birthdate,
         maritalstatus = p_maritalstatus,
         gender = p_gender
   WHERE businessentityid = p_businessentityid;
EXCEPTION WHEN OTHERS THEN
  -- Source swallows the error and logs it via dbo.uspLogError; mimic "log and continue".
  RAISE WARNING 'uspUpdateEmployee error: %', SQLERRM;
END;
$$ LANGUAGE plpgsql;
