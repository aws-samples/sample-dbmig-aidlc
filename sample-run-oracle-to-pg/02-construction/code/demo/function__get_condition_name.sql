CREATE OR REPLACE FUNCTION demo.get_condition_name(p_condition_id numeric)
RETURNS varchar LANGUAGE plpgsql STABLE AS $$
DECLARE
    v_name demo.conditions.name%TYPE;
BEGIN
    SELECT name INTO STRICT v_name FROM demo.conditions WHERE id = p_condition_id;   -- STRICT: keep Oracle NO_DATA_FOUND
    RETURN v_name;
EXCEPTION
    WHEN NO_DATA_FOUND THEN
        RETURN 'Unknown';
END $$;
