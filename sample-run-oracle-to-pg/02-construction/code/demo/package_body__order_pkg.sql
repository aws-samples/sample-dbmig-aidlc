-- DEMO.ORDER_PKG (package body) -> flattened routines demo.order_pkg_*
-- NVL -> COALESCE; SYSTIMESTAMP/SYSDATE -> now(); RETURNING ... INTO preserved.

CREATE OR REPLACE FUNCTION demo.order_pkg_calculate_order_total(p_order_id bigint)
RETURNS numeric
AS $$
DECLARE
  v_total numeric := 0;
BEGIN
  SELECT COALESCE(SUM(book_price * quantity - COALESCE(discount, 0)), 0) INTO v_total
  FROM demo.order_items
  WHERE order_id = p_order_id;
  RETURN v_total;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION demo.order_pkg_get_customer_order_count(p_customer_id bigint)
RETURNS numeric
AS $$
DECLARE
  v_count numeric := 0;
BEGIN
  SELECT COUNT(*) INTO v_count FROM demo.orders WHERE customer_id = p_customer_id;
  RETURN v_count;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION demo.order_pkg_create_order(
    p_customer_id bigint,
    p_address_id  bigint)
RETURNS bigint
AS $$
DECLARE
  v_order_id demo.orders.id%TYPE;
BEGIN
  INSERT INTO demo.orders (customer_id, address_id, created_on, status, total_amount)
  VALUES (p_customer_id, p_address_id, now(), 'PENDING', 0)
  RETURNING id INTO v_order_id;
  RETURN v_order_id;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE PROCEDURE demo.order_pkg_add_order_item(
    p_order_id   bigint,
    p_listing_id bigint,
    p_quantity   numeric)
AS $$
DECLARE
  v_book_id demo.listings.book_id%TYPE;
  v_price   demo.listings.price%TYPE;
BEGIN
  SELECT book_id, price INTO STRICT v_book_id, v_price
  FROM demo.listings WHERE id = p_listing_id;

  INSERT INTO demo.order_items (order_id, book_id, listing_id, quantity, book_price)
  VALUES (p_order_id, v_book_id, p_listing_id, p_quantity, v_price);

  UPDATE demo.orders
     SET total_amount = demo.order_pkg_calculate_order_total(p_order_id),
         updated_on = now()
   WHERE id = p_order_id;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE PROCEDURE demo.order_pkg_update_order_status(
    p_order_id bigint,
    p_status   varchar)
AS $$
BEGIN
  UPDATE demo.orders
     SET status = p_status,
         updated_on = now(),
         shipped_date   = CASE WHEN p_status = 'SHIPPED'   THEN now() END,
         delivered_date = CASE WHEN p_status = 'DELIVERED' THEN now() END,
         cancelled_date = CASE WHEN p_status = 'CANCELLED' THEN now() END
   WHERE id = p_order_id;
END;
$$ LANGUAGE plpgsql;
