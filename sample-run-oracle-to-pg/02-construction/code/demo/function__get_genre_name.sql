-- DEMO.GET_GENRE_NAME. %TYPE kept (PostgreSQL supports it). SELECT INTO STRICT reproduces Oracle's
-- NO_DATA_FOUND, which the source handles by returning 'Unknown'.
CREATE OR REPLACE FUNCTION demo.get_genre_name(p_genre_id numeric)
RETURNS varchar LANGUAGE plpgsql STABLE AS $$
DECLARE
    v_name demo.genres.name%TYPE;
BEGIN
    SELECT name INTO STRICT v_name FROM demo.genres WHERE id = p_genre_id;
    RETURN v_name;
EXCEPTION
    WHEN NO_DATA_FOUND THEN
        RETURN 'Unknown';
END $$;
