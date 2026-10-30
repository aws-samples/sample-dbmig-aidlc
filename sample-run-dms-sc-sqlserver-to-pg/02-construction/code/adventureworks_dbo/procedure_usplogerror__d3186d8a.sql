-- MANUAL reconversion of dbo.uspLogError (7811 x2). Reconverted because the HUMANRESOURCES
-- procedures call it from their error handlers.
--
-- DMS SC output: the INSERT into ErrorLog is commented out (CURRENT_USER / ERROR_*() flagged
-- 7811) and the body reads an undeclared variable error_catch$ERROR_NUMBER, so every call
-- fails, falls into its own handler and returns -1. Errors were never logged.
--
-- SQL Server reads ERROR_NUMBER()/ERROR_MESSAGE() of the caller's CATCH block. A PostgreSQL
-- procedure cannot see its caller's exception (GET STACKED DIAGNOSTICS works only inside
-- the handler itself), so the caller passes SQLSTATE / SQLERRM in. Called without them it
-- returns without logging, like the source when ERROR_NUMBER() IS NULL.
-- XACT_STATE() = -1 has no equivalent and is not needed: by the time a PL/pgSQL handler
-- runs, the failed block's subtransaction is already rolled back, so the INSERT is allowed.
-- ErrorNumber is an int: a numeric SQLSTATE (e.g. 23514) is stored as-is, any other
-- (e.g. P0001) as 0; the SQLSTATE is also kept as the message prefix.
-- engines/sqlserver-to-postgresql/checks/non-portable-constructs.md (TRY/CATCH, ERROR_*()).
DROP PROCEDURE IF EXISTS adventureworks_dbo.usplogerror(integer, integer);
DROP PROCEDURE IF EXISTS adventureworks_dbo.usplogerror(integer, integer, text, text, text);
CREATE PROCEDURE adventureworks_dbo.usplogerror(
    INOUT par_errorlogid integer DEFAULT 0,
    INOUT return_code    integer DEFAULT 0,
    IN    par_sqlstate   text    DEFAULT NULL,
    IN    par_message    text    DEFAULT NULL,
    IN    par_procedure  text    DEFAULT NULL)
LANGUAGE plpgsql
AS
$BODY$
BEGIN
    par_errorlogid := 0;
    IF par_sqlstate IS NULL THEN
        RETURN;                                   -- no error information to log
    END IF;
    INSERT INTO adventureworks_dbo.errorlog
        (username, errornumber, errorseverity, errorstate, errorprocedure, errorline, errormessage)
    VALUES
        (current_user,
         CASE WHEN par_sqlstate ~ '^[0-9]+$' THEN par_sqlstate::integer ELSE 0 END,
         NULL, NULL, par_procedure, NULL,
         par_sqlstate || ': ' || coalesce(par_message, ''))
    RETURNING errorlogid INTO par_errorlogid;
EXCEPTION
    WHEN OTHERS THEN
        RAISE NOTICE 'An error occurred in stored procedure uspLogError: %', SQLERRM;
        return_code := -1;
END;
$BODY$;
