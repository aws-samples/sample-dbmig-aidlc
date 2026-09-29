-- TRY/CATCH (error logged and swallowed) -> EXCEPTION WHEN OTHERS: the block's update is undone,
-- the error is logged via dbo.usplogerror (parameters, not ambient ERROR_*()) and NOT re-raised —
-- same observable result as SQL Server. datetime param into a date column truncates in both.
CREATE OR REPLACE PROCEDURE dbo.uspupdateauthorlogin(p_businessentityid integer, p_organizationnode varchar(4000), p_loginid varchar(256), p_jobtitle varchar(50), p_hiredate timestamp(3), p_currentflag boolean)
LANGUAGE plpgsql AS $$
DECLARE
    v_msg text; v_state text; v_id integer;
BEGIN
    UPDATE dbo.author SET organizationnode = p_organizationnode, loginid = p_loginid, jobtitle = p_jobtitle, hiredate = p_hiredate::date, currentflag = p_currentflag WHERE businessentityid = p_businessentityid;
EXCEPTION WHEN OTHERS THEN
    GET STACKED DIAGNOSTICS v_msg = MESSAGE_TEXT, v_state = RETURNED_SQLSTATE;
    CALL dbo.usplogerror(v_id, 0, 16, 1, 'uspUpdateAuthorLogin', NULL, v_state || ': ' || v_msg);
END $$;
