-- Converted from Oracle DEMO.GET_CONDITION_NAME -> PostgreSQL demo.get_condition_name
-- Decisions:
--   Oracle SELECT ... INTO raises NO_DATA_FOUND when no row matches; plain PL/pgSQL
--   SELECT INTO does NOT. Use SELECT ... INTO STRICT so the exception handler below
--   still fires and the function returns 'Unknown' exactly as in Oracle.
--   Ref: non-portable-constructs.md → PL/SQL → PL/pgSQL (SELECT … INTO STRICT)
--   conditions.name%TYPE -> varchar(255) (the column's converted type)
--   Reads a table -> STABLE (not IMMUTABLE).

CREATE OR REPLACE FUNCTION demo.get_condition_name(p_condition_id numeric)
RETURNS varchar
LANGUAGE plpgsql
STABLE
AS $$
DECLARE
    v_name demo.conditions.name%TYPE;
BEGIN
    SELECT name INTO STRICT v_name
    FROM demo.conditions
    WHERE id = p_condition_id;
    RETURN v_name;
EXCEPTION
    WHEN NO_DATA_FOUND THEN
        RETURN 'Unknown';
END;
$$;
