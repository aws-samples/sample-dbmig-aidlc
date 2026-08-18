-- Converted from Oracle DEMO.VALIDATION_PKG (spec + body) -> PostgreSQL demo.validation_pkg_*
-- Package flattening: PostgreSQL has no packages; each subprogram becomes a schema-level
-- routine named <package>_<subprogram>. Ref: checks/package-naming.md
-- No name collisions were reported by convert-code for this package.
--
-- Decisions:
--   REGEXP_LIKE(x, p)     -> x ~ p
--   REGEXP_REPLACE(x,p,r) -> regexp_replace(x, p, r, 'g')
--       *** Oracle replaces ALL matches; PostgreSQL replaces only the FIRST unless the 'g'
--       flag is supplied. Without 'g' the ISBN digit-stripping would be wrong. ***
--       Ref: non-portable-constructs.md → REGEXP_REPLACE
--   Functions return NUMBER 0/1 in Oracle -> kept as numeric (not boolean) so callers and
--       the equivalence harness compare identical values.
--   Pure string/number logic, no table access -> IMMUTABLE.

CREATE OR REPLACE FUNCTION demo.validation_pkg_is_valid_email(p_email varchar)
RETURNS numeric
LANGUAGE plpgsql
IMMUTABLE
AS $$
BEGIN
    RETURN CASE
        WHEN p_email ~ '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$'
        THEN 1
        ELSE 0
    END;
END;
$$;

CREATE OR REPLACE FUNCTION demo.validation_pkg_is_valid_isbn(p_isbn varchar)
RETURNS numeric
LANGUAGE plpgsql
IMMUTABLE
AS $$
BEGIN
    RETURN CASE
        WHEN length(regexp_replace(p_isbn, '[^0-9X]', '', 'g')) IN (10, 13) THEN 1
        ELSE 0
    END;
END;
$$;

CREATE OR REPLACE FUNCTION demo.validation_pkg_is_valid_price(p_price numeric)
RETURNS numeric
LANGUAGE plpgsql
IMMUTABLE
AS $$
BEGIN
    RETURN CASE
        WHEN p_price > 0 AND p_price < 10000 THEN 1
        ELSE 0
    END;
END;
$$;
