-- DEMO.BOOK_PKG (package body) -> flattened routines demo.book_pkg_*
-- NVL -> COALESCE; SYSTIMESTAMP -> now(); intra-package calls become calls to the flattened names.

CREATE OR REPLACE FUNCTION demo.book_pkg_get_available_quantity(p_book_id bigint)
RETURNS numeric
AS $$
DECLARE
  v_qty numeric := 0;
BEGIN
  SELECT COALESCE(SUM(quantity), 0) INTO v_qty
  FROM demo.listings
  WHERE book_id = p_book_id AND status = 1 AND listing_type = 'STORE';
  RETURN v_qty;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION demo.book_pkg_get_avg_price(p_book_id bigint)
RETURNS numeric
AS $$
DECLARE
  v_avg numeric := 0;
BEGIN
  SELECT COALESCE(AVG(price), 0) INTO v_avg
  FROM demo.listings
  WHERE book_id = p_book_id AND status = 1 AND listing_type = 'STORE';
  RETURN v_avg;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION demo.book_pkg_is_in_stock(p_book_id bigint)
RETURNS numeric
AS $$
BEGIN
  RETURN CASE WHEN demo.book_pkg_get_available_quantity(p_book_id) > 0 THEN 1 ELSE 0 END;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE PROCEDURE demo.book_pkg_get_book_details(
    p_book_id   bigint,
    OUT p_title     varchar,
    OUT p_author    varchar,
    OUT p_total_qty numeric,
    OUT p_avg_price numeric)
AS $$
BEGIN
  SELECT title, author INTO STRICT p_title, p_author
  FROM demo.books WHERE id = p_book_id;
  p_total_qty := demo.book_pkg_get_available_quantity(p_book_id);
  p_avg_price := demo.book_pkg_get_avg_price(p_book_id);
END;
$$ LANGUAGE plpgsql;
