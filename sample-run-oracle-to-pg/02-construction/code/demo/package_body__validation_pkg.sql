-- DEMO.VALIDATION_PKG (package body) -> flattened routines demo.validation_pkg_*
-- REGEXP_LIKE -> the ~ operator; Oracle REGEXP_REPLACE replaces all -> add the 'g' flag in PG.
-- Pure input->output functions marked IMMUTABLE.

CREATE OR REPLACE FUNCTION demo.validation_pkg_is_valid_email(p_email varchar)
RETURNS numeric
IMMUTABLE
AS $$
BEGIN
  RETURN CASE
    WHEN p_email ~ '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$' THEN 1
    ELSE 0
  END;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION demo.validation_pkg_is_valid_isbn(p_isbn varchar)
RETURNS numeric
IMMUTABLE
AS $$
BEGIN
  RETURN CASE
    WHEN length(regexp_replace(p_isbn, '[^0-9X]', '', 'g')) IN (10, 13) THEN 1
    ELSE 0
  END;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION demo.validation_pkg_is_valid_price(p_price numeric)
RETURNS numeric
IMMUTABLE
AS $$
BEGIN
  RETURN CASE
    WHEN p_price > 0 AND p_price < 10000 THEN 1
    ELSE 0
  END;
END;
$$ LANGUAGE plpgsql;
