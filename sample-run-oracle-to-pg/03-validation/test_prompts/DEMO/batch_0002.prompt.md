<!-- dbmig test-generation prompt  batch 2/4
     Write one test spec (YAML) per object:
       - PACKAGE DEMO.INVENTORY_PKG -> tests/DEMO/package__inventory_pkg.test.yaml
       - PACKAGE DEMO.ORDER_PKG -> tests/DEMO/package__order_pkg.test.yaml
     Then set each unit's status 'generated' in test-manifest-DEMO.yaml. -->
<!-- PARTIAL coverage ORDER_PKG: empty referenced tables: ORDERS, ORDER_ITEMS -->

=== CONTEXT ===
Shared tests context for this run: `migrations/<project>/03-validation/_context-tests.md`. Read it once per session if you have not already — it holds the customer-specific rules (highest precedence), datatype map, engine checks and playbook index this task relies on. Do not skip it.

=== TASK — GENERATE EQUIVALENCE TESTS ===
Generate equivalence tests that prove each of the 2 converted PostgreSQL (Aurora PostgreSQL compatible) objects below (one spec file per object, as listed in the header) behaves the same as the Oracle source: same input → same return value (functions) or same net effect (procedures). Tests run on BOTH engines and the results are compared. Use the spec format and Rules in the context above.

### PACKAGE DEMO.INVENTORY_PKG — write a **function and/or procedure**-shape spec
--- SOURCE (PACKAGE) — DEMO.INVENTORY_PKG ---
CREATE OR REPLACE EDITIONABLE PACKAGE "DEMO"."INVENTORY_PKG" AS
    -- Reduce inventory after purchase
    PROCEDURE reduce_inventory(
        p_listing_id NUMBER,
        p_quantity NUMBER
    );

    -- Check if sufficient inventory exists
    FUNCTION has_sufficient_inventory(
        p_listing_id NUMBER,
        p_quantity NUMBER
    ) RETURN NUMBER;

    -- Get low stock items
    FUNCTION get_low_stock_count(p_threshold NUMBER DEFAULT 5) RETURN NUMBER;
END inventory_pkg;

CREATE OR REPLACE EDITIONABLE PACKAGE BODY "DEMO"."INVENTORY_PKG" AS
    PROCEDURE reduce_inventory(
        p_listing_id NUMBER,
        p_quantity NUMBER
    ) IS
        v_current_qty listings.quantity%TYPE;
    BEGIN
        SELECT quantity INTO v_current_qty
        FROM listings
        WHERE id = p_listing_id
        FOR UPDATE;

        IF v_current_qty < p_quantity THEN
            RAISE_APPLICATION_ERROR(-20001, 'Insufficient inventory');
        END IF;

        UPDATE listings
        SET quantity = quantity - p_quantity,
            updated_on = SYSTIMESTAMP
        WHERE id = p_listing_id;
    END;

    FUNCTION has_sufficient_inventory(
        p_listing_id NUMBER,
        p_quantity NUMBER
    ) RETURN NUMBER IS
        v_current_qty listings.quantity%TYPE;
    BEGIN
        SELECT quantity INTO v_current_qty
        FROM listings
        WHERE id = p_listing_id;

        RETURN CASE WHEN v_current_qty >= p_quantity THEN 1 ELSE 0 END;
    END;

    FUNCTION get_low_stock_count(p_threshold NUMBER DEFAULT 5) RETURN NUMBER IS
        v_count PLS_INTEGER;
    BEGIN
        SELECT COUNT(*)
        INTO v_count
        FROM listings
        WHERE status = 1
          AND listing_type = 'STORE'
          AND quantity <= p_threshold;
        RETURN v_count;
    END;
END inventory_pkg;

--- CONVERTED TARGET CODE (PostgreSQL) — use these exact routine names and signatures in target_sql / call_target ---
-- Package INVENTORY_PKG (spec + body) flattened to <package>_<subprogram>.
-- RAISE_APPLICATION_ERROR(-20001) -> ERRCODE 'U0001'. Caller owns the transaction.
CREATE OR REPLACE PROCEDURE demo.inventory_pkg_reduce_inventory(p_listing_id numeric, p_quantity numeric)
LANGUAGE plpgsql AS $$
DECLARE
    v_current_qty demo.listings.quantity%TYPE;
BEGIN
    SELECT quantity INTO STRICT v_current_qty FROM demo.listings WHERE id = p_listing_id FOR UPDATE;
    IF v_current_qty < p_quantity THEN
        RAISE EXCEPTION 'Insufficient inventory' USING ERRCODE = 'U0001';
    END IF;
    UPDATE demo.listings
    SET quantity = quantity - p_quantity, updated_on = current_timestamp
    WHERE id = p_listing_id;
END $$;

CREATE OR REPLACE FUNCTION demo.inventory_pkg_has_sufficient_inventory(p_listing_id numeric, p_quantity numeric)
RETURNS numeric LANGUAGE plpgsql STABLE AS $$
DECLARE
    v_current_qty demo.listings.quantity%TYPE;
BEGIN
    SELECT quantity INTO v_current_qty FROM demo.listings WHERE id = p_listing_id;
    -- Oracle: unhandled NO_DATA_FOUND inside a function called from SQL yields NULL.
    IF NOT FOUND THEN
        RETURN NULL;
    END IF;
    RETURN CASE WHEN v_current_qty >= p_quantity THEN 1 ELSE 0 END;
END $$;

CREATE OR REPLACE FUNCTION demo.inventory_pkg_get_low_stock_count(p_threshold numeric DEFAULT 5)
RETURNS numeric LANGUAGE plpgsql STABLE AS $$
DECLARE
    v_count bigint;       -- PLS_INTEGER
BEGIN
    SELECT count(*) INTO v_count
    FROM demo.listings
    WHERE status = 1 AND listing_type = 'STORE' AND quantity <= p_threshold;
    RETURN v_count;
END $$;

### PACKAGE DEMO.ORDER_PKG — write a **function and/or procedure**-shape spec
--- SOURCE (PACKAGE) — DEMO.ORDER_PKG ---
CREATE OR REPLACE EDITIONABLE PACKAGE "DEMO"."ORDER_PKG" AS
    -- Calculate order total
    FUNCTION calculate_order_total(p_order_id NUMBER) RETURN NUMBER;

    -- Get customer order count
    FUNCTION get_customer_order_count(p_customer_id NUMBER) RETURN NUMBER;

    -- Create new order
    FUNCTION create_order(
        p_customer_id NUMBER,
        p_address_id NUMBER
    ) RETURN NUMBER;

    -- Add item to order
    PROCEDURE add_order_item(
        p_order_id NUMBER,
        p_listing_id NUMBER,
        p_quantity NUMBER
    );

    -- Update order status
    PROCEDURE update_order_status(
        p_order_id NUMBER,
        p_status VARCHAR2
    );
END order_pkg;

CREATE OR REPLACE EDITIONABLE PACKAGE BODY "DEMO"."ORDER_PKG" AS
    FUNCTION calculate_order_total(p_order_id NUMBER) RETURN NUMBER IS
        v_total NUMBER := 0;
    BEGIN
        SELECT NVL(SUM(book_price * quantity - NVL(discount, 0)), 0)
        INTO v_total
        FROM order_items
        WHERE order_id = p_order_id;
        RETURN v_total;
    END;

    FUNCTION get_customer_order_count(p_customer_id NUMBER) RETURN NUMBER IS
        v_count NUMBER := 0;
    BEGIN
        SELECT COUNT(*)
        INTO v_count
        FROM orders
        WHERE customer_id = p_customer_id;
        RETURN v_count;
    END;

    FUNCTION create_order(
        p_customer_id NUMBER,
        p_address_id NUMBER
    ) RETURN NUMBER IS
        v_order_id orders.id%TYPE;
    BEGIN
        INSERT INTO orders (customer_id, address_id, created_on, status, total_amount)
        VALUES (p_customer_id, p_address_id, SYSTIMESTAMP, 'PENDING', 0)
        RETURNING id INTO v_order_id;
        RETURN v_order_id;
    END;

    PROCEDURE add_order_item(
        p_order_id NUMBER,
        p_listing_id NUMBER,
        p_quantity NUMBER
    ) IS
        v_book_id listings.book_id%TYPE;
        v_price listings.price%TYPE;
    BEGIN
        SELECT book_id, price
        INTO v_book_id, v_price
        FROM listings
        WHERE id = p_listing_id;

        INSERT INTO order_items (order_id, book_id, listing_id, quantity, book_price)
        VALUES (p_order_id, v_book_id, p_listing_id, p_quantity, v_price);

        -- Update order total
        UPDATE orders
        SET total_amount = calculate_order_total(p_order_id),
            updated_on = SYSTIMESTAMP
        WHERE id = p_order_id;
    END;

    PROCEDURE update_order_status(
        p_order_id NUMBER,
        p_status VARCHAR2
    ) IS
    BEGIN
        UPDATE orders
        SET status = p_status,
            updated_on = SYSTIMESTAMP,
            shipped_date = CASE WHEN p_status = 'SHIPPED' THEN SYSDATE END,
            delivered_date = CASE WHEN p_status = 'DELIVERED' THEN SYSDATE END,
            cancelled_date = CASE WHEN p_status = 'CANCELLED' THEN SYSDATE END
        WHERE id = p_order_id;
    END;
END order_pkg;

--- CONVERTED TARGET CODE (PostgreSQL) — use these exact routine names and signatures in target_sql / call_target ---
-- Package ORDER_PKG (spec + body) flattened to <package>_<subprogram>. Caller owns the transaction.
CREATE OR REPLACE FUNCTION demo.order_pkg_calculate_order_total(p_order_id numeric)
RETURNS numeric LANGUAGE plpgsql STABLE AS $$
DECLARE
    v_total numeric := 0;
BEGIN
    SELECT coalesce(sum(book_price * quantity - coalesce(discount, 0)), 0) INTO v_total
    FROM demo.order_items WHERE order_id = p_order_id;
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

-- VOLATILE (inserts). Returns the new identity value.
CREATE OR REPLACE FUNCTION demo.order_pkg_create_order(p_customer_id numeric, p_address_id numeric)
RETURNS numeric LANGUAGE plpgsql AS $$
DECLARE
    v_order_id demo.orders.id%TYPE;
BEGIN
    INSERT INTO demo.orders (customer_id, address_id, created_on, status, total_amount)
    VALUES (p_customer_id, p_address_id, current_timestamp, 'PENDING', 0)
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
    SET total_amount = demo.order_pkg_calculate_order_total(p_order_id), updated_on = current_timestamp
    WHERE id = p_order_id;
END $$;

-- SYSDATE (DATE, seconds precision) -> localtimestamp(0)
CREATE OR REPLACE PROCEDURE demo.order_pkg_update_order_status(p_order_id numeric, p_status varchar)
LANGUAGE plpgsql AS $$
BEGIN
    UPDATE demo.orders
    SET status = p_status,
        updated_on = current_timestamp,
        shipped_date   = CASE WHEN p_status = 'SHIPPED'   THEN localtimestamp(0) END,
        delivered_date = CASE WHEN p_status = 'DELIVERED' THEN localtimestamp(0) END,
        cancelled_date = CASE WHEN p_status = 'CANCELLED' THEN localtimestamp(0) END
    WHERE id = p_order_id;
END $$;

--- SAMPLED REAL DATA (use these actual values) ---
### LISTINGS  (columns: ID, BOOK_ID, SELLER_ID, PRICE, QUANTITY, CONDITION_ID, STATUS, LISTING_TYPE, ADMIN_NOTES, PROCESSED_AT, PROCESSED_BY, IS_FEATURED, IS_BESTSELLER, IS_NEW_ARRIVAL, CREATED_ON, UPDATED_ON)
  1 | 1 | 1 | 10.95 | 25 | 2 | 1 | SYSTEM |  |  |  | 1 | 0 | 1 | 2026-09-28 02:05:26.204692 | 
  2 | 2 | 1 | 13.95 | 3 | 3 | 1 | SYSTEM |  |  |  | 0 | 1 | 0 | 2026-09-28 02:05:26.208513 | 
  3 | 3 | 1 | 6.5 | 10 | 1 | 1 | SYSTEM |  |  |  | 1 | 1 | 0 | 2026-09-28 02:05:26.212295 | 
