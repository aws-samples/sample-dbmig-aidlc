-- Converted from Oracle DEMO.BOOK_PKG (spec + body) -> PostgreSQL demo.book_pkg_*
-- Package flattening -> <package>_<subprogram>. Ref: checks/package-naming.md
--
-- Decisions:
--   NVL -> COALESCE. Aggregate SELECT INTO always returns one row -> no STRICT needed.
--   get_book_details is a single-row lookup that Oracle would fail with NO_DATA_FOUND ->
--       SELECT INTO STRICT preserves that behavior.
--   Intra-package call get_available_quantity(...) -> demo.book_pkg_get_available_quantity(...)
--   Read-only routines -> STABLE.

CREATE OR REPLACE FUNCTION demo.book_pkg_get_available_quantity(p_book_id numeric)
RETURNS numeric
LANGUAGE plpgsql
STABLE
AS $$
DECLARE
    v_qty numeric := 0;
BEGIN
    SELECT coalesce(sum(quantity), 0)
    INTO v_qty
    FROM demo.listings
    WHERE book_id = p_book_id
      AND status = 1
      AND listing_type = 'STORE';
    RETURN v_qty;
END;
$$;

CREATE OR REPLACE FUNCTION demo.book_pkg_get_avg_price(p_book_id numeric)
RETURNS numeric
LANGUAGE plpgsql
STABLE
AS $$
DECLARE
    v_avg numeric := 0;
BEGIN
    SELECT coalesce(avg(price), 0)
    INTO v_avg
    FROM demo.listings
    WHERE book_id = p_book_id
      AND status = 1
      AND listing_type = 'STORE';
    RETURN v_avg;
END;
$$;

CREATE OR REPLACE FUNCTION demo.book_pkg_is_in_stock(p_book_id numeric)
RETURNS numeric
LANGUAGE plpgsql
STABLE
AS $$
BEGIN
    RETURN CASE WHEN demo.book_pkg_get_available_quantity(p_book_id) > 0 THEN 1 ELSE 0 END;
END;
$$;

CREATE OR REPLACE PROCEDURE demo.book_pkg_get_book_details(
    p_book_id       numeric,
    OUT p_title     varchar,
    OUT p_author    varchar,
    OUT p_total_qty numeric,
    OUT p_avg_price numeric
)
LANGUAGE plpgsql
AS $$
BEGIN
    SELECT title, author
    INTO STRICT p_title, p_author
    FROM demo.books
    WHERE id = p_book_id;

    p_total_qty := demo.book_pkg_get_available_quantity(p_book_id);
    p_avg_price := demo.book_pkg_get_avg_price(p_book_id);
END;
$$;
