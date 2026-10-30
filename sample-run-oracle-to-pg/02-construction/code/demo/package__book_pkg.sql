-- Package BOOK_PKG (spec + body) flattened to <package>_<subprogram> (checks/package-naming.md).
-- Calls between subprograms are rewritten to the flattened names.
CREATE OR REPLACE FUNCTION demo.book_pkg_get_available_quantity(p_book_id numeric)
RETURNS numeric LANGUAGE plpgsql STABLE AS $$
DECLARE
    v_qty demo.listings.quantity%TYPE := 0;
BEGIN
    SELECT coalesce(sum(quantity), 0) INTO v_qty
    FROM demo.listings
    WHERE book_id = p_book_id AND status = 1 AND listing_type = 'STORE';
    RETURN v_qty;
END $$;

-- v_avg is listings.price%TYPE (numeric(38,2)) on both engines, so AVG is rounded to 2 places
-- by the assignment in both.
CREATE OR REPLACE FUNCTION demo.book_pkg_get_avg_price(p_book_id numeric)
RETURNS numeric LANGUAGE plpgsql STABLE AS $$
DECLARE
    v_avg demo.listings.price%TYPE := 0;
BEGIN
    SELECT coalesce(avg(price), 0) INTO v_avg
    FROM demo.listings
    WHERE book_id = p_book_id AND status = 1 AND listing_type = 'STORE';
    RETURN v_avg;
END $$;

CREATE OR REPLACE FUNCTION demo.book_pkg_is_in_stock(p_book_id numeric)
RETURNS numeric LANGUAGE plpgsql STABLE AS $$
BEGIN
    RETURN CASE WHEN demo.book_pkg_get_available_quantity(p_book_id) > 0 THEN 1 ELSE 0 END;
END $$;

-- SELECT INTO STRICT: a missing book raises NO_DATA_FOUND, as in Oracle.
CREATE OR REPLACE PROCEDURE demo.book_pkg_get_book_details(
    p_book_id numeric,
    OUT p_title varchar,
    OUT p_author varchar,
    OUT p_total_qty numeric,
    OUT p_avg_price numeric)
LANGUAGE plpgsql AS $$
BEGIN
    SELECT title, author INTO STRICT p_title, p_author FROM demo.books WHERE id = p_book_id;
    p_total_qty := demo.book_pkg_get_available_quantity(p_book_id);
    p_avg_price := demo.book_pkg_get_avg_price(p_book_id);
END $$;
