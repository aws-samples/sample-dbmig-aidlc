-- DEMO.GET_CONDITION_NAME. %TYPE kept (PostgreSQL supports it). SELECT INTO STRICT reproduces Oracle's
-- NO_DATA_FOUND, which the source handles by returning 'Unknown'.
CREATE OR REPLACE FUNCTION demo.get_condition_name(p_condition_id numeric)
RETURNS varchar LANGUAGE plpgsql STABLE AS $$
DECLARE
    v_name demo.conditions.name%TYPE;
BEGIN
    SELECT name INTO STRICT v_name FROM demo.conditions WHERE id = p_condition_id;
    RETURN v_name;
EXCEPTION
    WHEN NO_DATA_FOUND THEN
        RETURN 'Unknown';
END $$;
