-- Redesign: SQL Server reads ERROR_NUMBER()/… ambiently inside CATCH; PostgreSQL callers pass
-- them (GET STACKED DIAGNOSTICS in the caller's handler). SCOPE_IDENTITY() -> RETURNING.
-- SUSER_SNAME() -> session_user. Error number: SQL Server numbers (e.g. 50000 = RAISERROR)
-- have no PostgreSQL equivalent; callers pass 50000 for user errors and 0 otherwise, and put
-- the SQLSTATE in the message.
CREATE OR REPLACE PROCEDURE dbo.usplogerror(
    INOUT p_errorlogid integer DEFAULT 0,
    p_errornumber integer DEFAULT NULL, p_severity integer DEFAULT NULL, p_state integer DEFAULT NULL,
    p_procedure varchar DEFAULT NULL, p_line integer DEFAULT NULL, p_message varchar DEFAULT NULL)
LANGUAGE plpgsql AS $$
BEGIN
    p_errorlogid := 0;
    IF p_errornumber IS NULL THEN
        RETURN;
    END IF;
    INSERT INTO dbo.errorlog (username, errornumber, errorseverity, errorstate, errorprocedure, errorline, errormessage)
    VALUES (session_user, p_errornumber, p_severity, p_state, p_procedure, p_line, p_message)
    RETURNING errorlogid INTO p_errorlogid;
EXCEPTION WHEN OTHERS THEN
    RAISE NOTICE 'An error occurred in stored procedure uspLogError: ';
    CALL dbo.uspprinterror(0, NULL, NULL, 'usplogerror', NULL, SQLERRM);
    p_errorlogid := -1;
END $$;
