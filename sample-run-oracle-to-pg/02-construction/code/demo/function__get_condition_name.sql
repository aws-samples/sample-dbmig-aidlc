-- DEMO.GET_CONDITION_NAME -> demo.get_condition_name
-- Oracle SELECT INTO raises NO_DATA_FOUND -> use SELECT INTO STRICT in PL/pgSQL.
CREATE OR REPLACE FUNCTION demo.get_condition_name(p_condition_id bigint)
RETURNS varchar
AS $$
DECLARE
  v_name demo.conditions.name%TYPE;
BEGIN
  SELECT name INTO STRICT v_name FROM demo.conditions WHERE id = p_condition_id;
  RETURN v_name;
EXCEPTION
  WHEN NO_DATA_FOUND THEN
    RETURN 'Unknown';
END;
$$ LANGUAGE plpgsql;
