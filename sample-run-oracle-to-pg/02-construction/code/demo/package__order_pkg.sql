-- Converted from Oracle DEMO.ORDER_PKG (spec + body) -> PostgreSQL demo.order_pkg_*
-- Package flattening -> <package>_<subprogram>. Ref: checks/package-naming.md
--
-- Decisions:
--   NVL -> COALESCE;  SYSTIMESTAMP / SYSDATE -> now()
--   INSERT ... RETURNING id INTO  -> identical in PL/pgSQL (RETURNING is supported).
--   create_order / add_order_item / update_order_status are VOLATILE (they write) — the
--       default, stated explicitly for clarity.
--   add_order_item: Oracle's SELECT INTO would raise NO_DATA_FOUND for a missing listing ->
--       SELECT INTO STRICT preserves that.
--   update_order_status: the CASE expressions have no ELSE, so a non-matching status writes
--       NULL over shipped_date / delivered_date / cancelled_date. That is the SOURCE behavior
--       and is preserved deliberately (do not "fix" it — equivalence testing compares net effect).
--       SYSDATE -> now(); the target columns are timestamp(0) so PostgreSQL truncates to the
--       second exactly as Oracle DATE did.
--   No COMMIT existed in these routines — the caller owns the transaction.

CREATE OR REPLACE FUNCTION demo.order_pkg_calculate_order_total(p_order_id numeric)
RETURNS numeric
LANGUAGE plpgsql
STABLE
AS $$
DECLARE
    v_total numeric := 0;
BEGIN
    SELECT coalesce(sum(book_price * quantity - coalesce(discount, 0)), 0)
    INTO v_total
    FROM demo.order_items
    WHERE order_id = p_order_id;
    RETURN v_total;
END;
$$;

CREATE OR REPLACE FUNCTION demo.order_pkg_get_customer_order_count(p_customer_id numeric)
RETURNS numeric
LANGUAGE plpgsql
STABLE
AS $$
DECLARE
    v_count numeric := 0;
BEGIN
    SELECT count(*)
    INTO v_count
    FROM demo.orders
    WHERE customer_id = p_customer_id;
    RETURN v_count;
END;
$$;

CREATE OR REPLACE FUNCTION demo.order_pkg_create_order(
    p_customer_id numeric,
    p_address_id  numeric
) RETURNS numeric
LANGUAGE plpgsql
VOLATILE
AS $$
DECLARE
    v_order_id demo.orders.id%TYPE;
BEGIN
    INSERT INTO demo.orders (customer_id, address_id, created_on, status, total_amount)
    VALUES (p_customer_id, p_address_id, now(), 'PENDING', 0)
    RETURNING id INTO v_order_id;
    RETURN v_order_id;
END;
$$;

CREATE OR REPLACE PROCEDURE demo.order_pkg_add_order_item(
    p_order_id   numeric,
    p_listing_id numeric,
    p_quantity   numeric
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_book_id demo.listings.book_id%TYPE;
    v_price   demo.listings.price%TYPE;
BEGIN
    SELECT book_id, price
    INTO STRICT v_book_id, v_price
    FROM demo.listings
    WHERE id = p_listing_id;

    INSERT INTO demo.order_items (order_id, book_id, listing_id, quantity, book_price)
    VALUES (p_order_id, v_book_id, p_listing_id, p_quantity, v_price);

    -- Update order total
    UPDATE demo.orders
    SET total_amount = demo.order_pkg_calculate_order_total(p_order_id),
        updated_on   = now()
    WHERE id = p_order_id;
END;
$$;

CREATE OR REPLACE PROCEDURE demo.order_pkg_update_order_status(
    p_order_id numeric,
    p_status   varchar
)
LANGUAGE plpgsql
AS $$
BEGIN
    UPDATE demo.orders
    SET status         = p_status,
        updated_on     = now(),
        shipped_date   = CASE WHEN p_status = 'SHIPPED'   THEN now() END,
        delivered_date = CASE WHEN p_status = 'DELIVERED' THEN now() END,
        cancelled_date = CASE WHEN p_status = 'CANCELLED' THEN now() END
    WHERE id = p_order_id;
END;
$$;
