-- DEMO.GET_GENRE_NAME -> demo.get_genre_name
CREATE OR REPLACE FUNCTION demo.get_genre_name(p_genre_id bigint)
RETURNS varchar
AS $$
DECLARE
  v_name demo.genres.name%TYPE;
BEGIN
  SELECT name INTO STRICT v_name FROM demo.genres WHERE id = p_genre_id;
  RETURN v_name;
EXCEPTION
  WHEN NO_DATA_FOUND THEN
    RETURN 'Unknown';
END;
$$ LANGUAGE plpgsql;
