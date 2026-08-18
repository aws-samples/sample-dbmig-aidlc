-- Converted from Oracle DEMO.GET_GENRE_NAME -> PostgreSQL demo.get_genre_name
-- Decisions: same pattern as get_condition_name —
--   SELECT ... INTO STRICT preserves Oracle's NO_DATA_FOUND -> 'Unknown' behavior.
--   Reads a table -> STABLE.

CREATE OR REPLACE FUNCTION demo.get_genre_name(p_genre_id numeric)
RETURNS varchar
LANGUAGE plpgsql
STABLE
AS $$
DECLARE
    v_name demo.genres.name%TYPE;
BEGIN
    SELECT name INTO STRICT v_name
    FROM demo.genres
    WHERE id = p_genre_id;
    RETURN v_name;
EXCEPTION
    WHEN NO_DATA_FOUND THEN
        RETURN 'Unknown';
END;
$$;
