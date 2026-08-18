-- Converted from Oracle DEMO.GET_CUSTOMER_FULL_NAME -> PostgreSQL demo.get_customer_full_name
-- Decisions:
--   SELECT ... INTO STRICT preserves Oracle's NO_DATA_FOUND -> 'Unknown Customer'.
--
--   *** SEMANTIC DIFFERENCE HANDLED — string concatenation with NULL ***
--   Oracle treats NULL as an empty string in `||`, so a NULL first_name yields ' Smith'.
--   PostgreSQL propagates NULL: NULL || ' ' || 'Smith' = NULL, which would change the
--   result AND bypass the intended output. COALESCE on each operand reproduces Oracle's
--   behavior exactly. Ref: equivalence-spec.md §6 (empty string / NULL differences).
--
--   Reads a table -> STABLE.

CREATE OR REPLACE FUNCTION demo.get_customer_full_name(p_customer_id numeric)
RETURNS varchar
LANGUAGE plpgsql
STABLE
AS $$
DECLARE
    v_name varchar(500);
BEGIN
    SELECT coalesce(first_name, '') || ' ' || coalesce(last_name, '')
    INTO STRICT v_name
    FROM demo.customers
    WHERE id = p_customer_id;
    RETURN v_name;
EXCEPTION
    WHEN NO_DATA_FOUND THEN
        RETURN 'Unknown Customer';
END;
$$;
