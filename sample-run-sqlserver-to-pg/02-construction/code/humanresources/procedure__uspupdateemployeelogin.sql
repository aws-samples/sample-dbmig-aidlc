-- HumanResources.uspUpdateEmployeeLogin -> humanresources.uspupdateemployeelogin
-- @OrganizationNode hierarchyid -> text (path string); dbo.Flag -> boolean; dbo.uspLogError -> RAISE.
CREATE OR REPLACE PROCEDURE humanresources.uspupdateemployeelogin(
    p_businessentityid integer,
    p_organizationnode text,
    p_loginid          varchar,
    p_jobtitle         varchar,
    p_hiredate         timestamp,
    p_currentflag      boolean)
AS $$
BEGIN
  UPDATE humanresources.employee
     SET organizationnode = p_organizationnode,
         loginid = p_loginid,
         jobtitle = p_jobtitle,
         hiredate = p_hiredate,
         currentflag = p_currentflag
   WHERE businessentityid = p_businessentityid;
EXCEPTION WHEN OTHERS THEN
  -- Source swallows the error and logs it via dbo.uspLogError; mimic "log and continue".
  RAISE WARNING 'uspUpdateEmployee error: %', SQLERRM;
END;
$$ LANGUAGE plpgsql;
