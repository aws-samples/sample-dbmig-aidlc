-- Package VALIDATION_PKG (spec + body) flattened to <package>_<subprogram>.
-- REGEXP_LIKE -> ~ (regexp_like() is also native since PG 15). REGEXP_REPLACE replaces ALL matches
-- in Oracle; PostgreSQL needs the 'g' flag (checks/non-portable-constructs.md).
-- Oracle LENGTH('') is NULL; PostgreSQL length('') is 0. Both give 0 here (NULL IN (...) -> ELSE 0).
CREATE OR REPLACE FUNCTION demo.validation_pkg_is_valid_email(p_email varchar)
RETURNS numeric LANGUAGE plpgsql IMMUTABLE AS $$
BEGIN
    RETURN CASE WHEN p_email ~ '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$' THEN 1 ELSE 0 END;
END $$;

CREATE OR REPLACE FUNCTION demo.validation_pkg_is_valid_isbn(p_isbn varchar)
RETURNS numeric LANGUAGE plpgsql IMMUTABLE AS $$
BEGIN
    RETURN CASE WHEN length(regexp_replace(p_isbn, '[^0-9X]', '', 'g')) IN (10, 13) THEN 1 ELSE 0 END;
END $$;

CREATE OR REPLACE FUNCTION demo.validation_pkg_is_valid_price(p_price numeric)
RETURNS numeric LANGUAGE plpgsql IMMUTABLE AS $$
BEGIN
    RETURN CASE WHEN p_price > 0 AND p_price < 10000 THEN 1 ELSE 0 END;
END $$;
