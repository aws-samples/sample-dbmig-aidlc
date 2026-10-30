CREATE OR REPLACE PROCEDURE adventureworks_dbo.usplogerror(INOUT par_errorlogid INTEGER DEFAULT 0, INOUT return_code int DEFAULT 0)
AS 
$BODY$
/* uspLogError logs error information in the ErrorLog table about the */
/* error that caused execution to jump to the CATCH block of a */
/* TRY...CATCH construct. This should be executed from within the scope */
/* of a CATCH block otherwise it will return without inserting error */
/* information. */
/* contains the ErrorLogID of the row inserted */
/* by uspLogError in the ErrorLog table */
BEGIN
    /* Output parameter value of 0 indicates that error */
    /* information was not logged */
    par_ErrorLogID := 0;

    BEGIN
        /* Return if there is no error information to log */
        IF error_catch$ERROR_NUMBER IS NULL THEN
            RETURN;
        END IF;
        /* Return if inside an uncommittable transaction. */
        /* Data insertion/modification is not allowed when */
        /* a transaction is in an uncommittable state. */
        
        /*
        [7811 - Severity CRITICAL - PostgreSQL doesn't support the XACT_STATE() function. DMS SC skips this unsupported function in the converted code. Create a user-defined function to replace the unsupported function.]
        IF XACT_STATE() = -1
                BEGIN
                    PRINT 'Cannot log error since the current transaction is in an uncommittable state. '
                        + 'Rollback the transaction before executing uspLogError in order to successfully log error information.';
                    RETURN;
                END
        */
        
        /*
        [7811 - Severity CRITICAL - PostgreSQL doesn't support the CURRENT_USER() function. DMS SC skips this unsupported function in the converted code. Create a user-defined function to replace the unsupported function.]
        INSERT [dbo].[ErrorLog]
                    (
                    [UserName],
                    [ErrorNumber],
                    [ErrorSeverity],
                    [ErrorState],
                    [ErrorProcedure],
                    [ErrorLine],
                    [ErrorMessage]
                    )
                VALUES
                    (
                    CONVERT(sysname, CURRENT_USER),
                    ERROR_NUMBER(),
                    ERROR_SEVERITY(),
                    ERROR_STATE(),
                    ERROR_PROCEDURE(),
                    ERROR_LINE(),
                    ERROR_MESSAGE()
                    );
        */
        /* Pass back the ErrorLogID of the row inserted */
        par_ErrorLogID := LASTVAL();
        EXCEPTION
            WHEN OTHERS THEN
                RAISE NOTICE 'An error occurred in stored procedure uspLogError: ';
                CALL adventureworks_dbo.uspprinterror();
                return_code := - 1;
                RETURN;
    END;
END;
$BODY$
LANGUAGE plpgsql;