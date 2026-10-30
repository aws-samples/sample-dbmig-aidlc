CREATE OR REPLACE PROCEDURE adventureworks_dbo.uspprinterror()
AS 
$BODY$
/* uspPrintError prints error information about the error that caused */
/* execution to jump to the CATCH block of a TRY...CATCH construct. */
/* Should be executed from within the scope of a CATCH block otherwise */
/* it will return without printing any error information. */
BEGIN
    /* Print error information. */
    RAISE NOTICE '%', 'Error ' || CAST (error_catch$ERROR_NUMBER AS VARCHAR(50)) || ', Severity ' || CAST (error_catch$ERROR_SEVERITY AS VARCHAR(5)) || ', State ' || CAST (error_catch$ERROR_STATE AS VARCHAR(5)) || ', Procedure ' || COALESCE(error_catch$ERROR_PROCEDURE, '-') || ', Line ' || CAST (error_catch$ERROR_LINE AS VARCHAR(5));
    RAISE NOTICE '%', error_catch$ERROR_MESSAGE;
END;
$BODY$
LANGUAGE plpgsql;