-- MANUAL reconversion of HumanResources.dEmployee (DMS SC produced no output, 7809).
-- INSTEAD OF DELETE on a TABLE does not exist in PostgreSQL (only on views): a BEFORE DELETE row
-- trigger that raises gives the same net effect — the delete is rejected and the transaction must
-- roll back (the source RAISERRORs and ROLLBACKs). engines/sqlserver-to-postgresql/checks/non-portable-constructs.md §2
CREATE OR REPLACE FUNCTION adventureworks_humanresources.fn_demployee() RETURNS trigger
LANGUAGE plpgsql AS
$BODY$
BEGIN
    RAISE EXCEPTION 'Employees cannot be deleted. They can only be marked as not current.'
        USING ERRCODE = 'P0001';
END;
$BODY$;
DROP TRIGGER IF EXISTS demployee ON adventureworks_humanresources.employee;
CREATE TRIGGER demployee BEFORE DELETE ON adventureworks_humanresources.employee
    FOR EACH ROW EXECUTE FUNCTION adventureworks_humanresources.fn_demployee();
