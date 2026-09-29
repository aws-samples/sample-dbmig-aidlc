-- ERROR_*() ambient state is not readable from a nested routine in PostgreSQL: the caller
-- passes the fields (checklist item 6). PRINT -> RAISE NOTICE.
CREATE OR REPLACE PROCEDURE dbo.uspprinterror(p_errornumber integer, p_severity integer, p_state integer,
                                              p_procedure varchar, p_line integer, p_message varchar)
LANGUAGE plpgsql AS $$
BEGIN
    RAISE NOTICE 'Error %, Severity %, State %, Procedure %, Line %',
        p_errornumber, p_severity, p_state, coalesce(p_procedure, '-'), p_line;
    RAISE NOTICE '%', p_message;
END $$;
