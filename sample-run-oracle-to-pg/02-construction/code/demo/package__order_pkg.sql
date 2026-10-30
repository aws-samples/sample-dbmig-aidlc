-- Package ORDER_PKG (spec + body) flattened to <package>_<subprogram>.
CREATE OR REPLACE FUNCTION demo.order_pkg_calculate_order_total(p_order_id numeric)
RETURNS numeric LANGUAGE plpgsql STABLE AS $$
DECLARE
    v_total numeric := 0;
BEGIN
    SELECT coalesce(sum(book_price * quantity - coalesce(discount, 0)), 0) INTO v_total
    FROM demo.order_items
    WHERE order_id = p_order_id;
    RETURN v_total;
END $$;

CREATE OR REPLACE FUNCTION demo.order_pkg_get_customer_order_count(p_customer_id numeric)
RETURNS numeric LANGUAGE plpgsql STABLE AS $$
DECLARE
    v_count numeric := 0;
BEGIN
    SELECT count(*) INTO v_count FROM demo.orders WHERE customer_id = p_customer_id;
    RETURN v_count;
END $$;

-- INSERT ... RETURNING id INTO works the same. VOLATILE (writes).
CREATE OR REPLACE FUNCTION demo.order_pkg_create_order(p_customer_id numeric, p_address_id numeric)
RETURNS numeric LANGUAGE plpgsql AS $$
DECLARE
    v_order_id demo.orders.id%TYPE;
BEGIN
    INSERT INTO demo.orders (customer_id, address_id, created_on, status, total_amount)
    VALUES (p_customer_id, p_address_id, localtimestamp, 'PENDING', 0)
    RETURNING id INTO v_order_id;
    RETURN v_order_id;
END $$;

CREATE OR REPLACE PROCEDURE demo.order_pkg_add_order_item(p_order_id numeric, p_listing_id numeric, p_quantity numeric)
LANGUAGE plpgsql AS $$
DECLARE
    v_book_id demo.listings.book_id%TYPE;
    v_price demo.listings.price%TYPE;
BEGIN
    SELECT book_id, price INTO STRICT v_book_id, v_price FROM demo.listings WHERE id = p_listing_id;
    INSERT INTO demo.order_items (order_id, book_id, listing_id, quantity, book_price)
    VALUES (p_order_id, v_book_id, p_listing_id, p_quantity, v_price);
    UPDATE demo.orders
    SET total_amount = demo.order_pkg_calculate_order_total(p_order_id), updated_on = localtimestamp
    WHERE id = p_order_id;
END $$;

-- SYSDATE into DATE columns (timestamp(0) on the target) -> localtimestamp(0).
CREATE OR REPLACE PROCEDURE demo.order_pkg_update_order_status(p_order_id numeric, p_status varchar)
LANGUAGE plpgsql AS $$
BEGIN
    UPDATE demo.orders
    SET status = p_status,
        updated_on = localtimestamp,
        shipped_date   = CASE WHEN p_status = 'SHIPPED'   THEN localtimestamp(0) END,
        delivered_date = CASE WHEN p_status = 'DELIVERED' THEN localtimestamp(0) END,
        cancelled_date = CASE WHEN p_status = 'CANCELLED' THEN localtimestamp(0) END
    WHERE id = p_order_id;
END $$;
