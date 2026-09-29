-- Package VALIDATION_PKG (spec + body) flattened to <package>_<subprogram>.
CREATE OR REPLACE FUNCTION demo.validation_pkg_is_valid_email(p_email varchar)
RETURNS numeric LANGUAGE plpgsql IMMUTABLE AS $$
BEGIN
    RETURN CASE WHEN p_email ~ '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$' THEN 1 ELSE 0 END;
END $$;

-- REGEXP_REPLACE replaces ALL matches in Oracle -> 'g' flag. Oracle '' is NULL, so an input that
-- strips to '' has LENGTH NULL there; in PG length('') = 0 — both fall to ELSE 0.
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
