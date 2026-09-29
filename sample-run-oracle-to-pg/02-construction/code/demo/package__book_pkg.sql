-- Package BOOK_PKG (spec + body) flattened to <package>_<subprogram>.
CREATE OR REPLACE FUNCTION demo.book_pkg_get_available_quantity(p_book_id numeric)
RETURNS numeric LANGUAGE plpgsql STABLE AS $$
DECLARE
    v_qty numeric := 0;   -- listings.quantity%TYPE (NUMBER(10)); SUM() is exact numeric
BEGIN
    SELECT coalesce(sum(quantity), 0) INTO v_qty
    FROM demo.listings
    WHERE book_id = p_book_id AND status = 1 AND listing_type = 'STORE';
    RETURN v_qty;
END $$;

CREATE OR REPLACE FUNCTION demo.book_pkg_get_avg_price(p_book_id numeric)
RETURNS numeric LANGUAGE plpgsql STABLE AS $$
DECLARE
    -- listings.price%TYPE = NUMBER(38,2): Oracle ROUNDS the AVG to 2 dp on assignment; keep it.
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

-- OUT params: CALL demo.book_pkg_get_book_details(id, NULL, NULL, NULL, NULL);
CREATE OR REPLACE PROCEDURE demo.book_pkg_get_book_details(
    p_book_id numeric, OUT p_title varchar, OUT p_author varchar,
    OUT p_total_qty numeric, OUT p_avg_price numeric)
LANGUAGE plpgsql AS $$
BEGIN
    SELECT title, author INTO STRICT p_title, p_author FROM demo.books WHERE id = p_book_id;
    p_total_qty := demo.book_pkg_get_available_quantity(p_book_id);
    p_avg_price := demo.book_pkg_get_avg_price(p_book_id);
END $$;
