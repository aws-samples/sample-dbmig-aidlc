-- TRY/CATCH (error logged and swallowed) -> EXCEPTION WHEN OTHERS: the block's update is undone,
-- the error is logged via dbo.usplogerror (parameters, not ambient ERROR_*()) and NOT re-raised —
-- same observable result as SQL Server. datetime param into a date column truncates in both.
CREATE OR REPLACE PROCEDURE dbo.uspupdateauthorpersonalinfo(p_businessentityid integer, p_nationalidnumber varchar(15), p_birthdate timestamp(3), p_maritalstatus char(1), p_gender char(1))
LANGUAGE plpgsql AS $$
DECLARE
    v_msg text; v_state text; v_id integer;
BEGIN
    UPDATE dbo.author SET nationalidnumber = p_nationalidnumber, birthdate = p_birthdate::date, maritalstatus = p_maritalstatus, gender = p_gender WHERE businessentityid = p_businessentityid;
EXCEPTION WHEN OTHERS THEN
    GET STACKED DIAGNOSTICS v_msg = MESSAGE_TEXT, v_state = RETURNED_SQLSTATE;
    CALL dbo.usplogerror(v_id, 0, 16, 1, 'uspUpdateAuthorPersonalInfo', NULL, v_state || ': ' || v_msg);
END $$;
