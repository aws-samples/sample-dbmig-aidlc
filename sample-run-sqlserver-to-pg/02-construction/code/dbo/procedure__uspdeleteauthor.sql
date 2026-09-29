-- TRY/CATCH + THROW -> EXCEPTION block + re-RAISE. @@ROWCOUNT = 0 -> NOT FOUND.
-- BEHAVIOURAL: SQL Server keeps the ErrorLog row written in CATCH before THROW; in PostgreSQL the
-- re-raised error aborts the caller's transaction, so that log row is rolled back with it
-- (no autonomous transactions). Log externally (application / pg log) if the row is required.
CREATE OR REPLACE PROCEDURE dbo.uspdeleteauthor(p_businessentityid integer)
LANGUAGE plpgsql AS $$
DECLARE
    v_msg text; v_state text; v_id integer;
BEGIN
    DELETE FROM dbo.author WHERE businessentityid = p_businessentityid;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'No author found with the provided BusinessEntityID.' USING ERRCODE = 'P0001';
    END IF;
EXCEPTION WHEN OTHERS THEN
    GET STACKED DIAGNOSTICS v_msg = MESSAGE_TEXT, v_state = RETURNED_SQLSTATE;
    CALL dbo.usplogerror(v_id, CASE WHEN v_state = 'P0001' THEN 50000 ELSE 0 END, 16, 1,
                         'uspDeleteAuthor', NULL, v_state || ': ' || v_msg);
    RAISE;
END $$;
