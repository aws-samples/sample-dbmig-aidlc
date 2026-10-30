<!-- dbmig code conversion prompt
     batch: 3/3
     Convert each object and SAVE PostgreSQL code to its output file:
       - PACKAGE DEMO.BOOK_PKG -> code/demo/package__book_pkg.sql
       - PACKAGE DEMO.INVENTORY_PKG -> code/demo/package__inventory_pkg.sql
       - PACKAGE DEMO.ORDER_PKG -> code/demo/package__order_pkg.sql
       - PACKAGE DEMO.REPORTING_PKG -> code/demo/package__reporting_pkg.sql
       - PACKAGE DEMO.VALIDATION_PKG -> code/demo/package__validation_pkg.sql
     Then set each unit's status to 'converted' in code-manifest-DEMO.yaml. -->

=== CONTEXT ===
Shared code context for this run: `migrations/<project>/02-construction/_context-code.md`. Read it once per session if you have not already — it holds the customer-specific rules (highest precedence), datatype map, engine checks and playbook index this task relies on. Do not skip it.

=== TASK ===
Convert the following Oracle stored code object to PostgreSQL (PL/pgSQL). Return only valid PostgreSQL, ready to execute. Packages/modules have no direct equivalent: map each routine to its own function/procedure. Note any construct that needs human review in a SQL comment. Qualify every created object with the target schema `demo` (derived from the source schema — do NOT use the connection's database/catalog name for qualification). Each object below is independent: convert each one and save it to its own output file (listed in the header).

=== CONSTRUCTS DETECTED IN THIS PROMPT'S SOURCE (apply the matching guidance; open the named playbook file when the context is not enough, and cite it in the conversion log) ===
- PIPELINED table function → RETURNS TABLE/SETOF; declared column types must match the query's actual types (checked only at execution) — see `skills/oracle-to-postgresql-playbook/references/sql-plsql/user-defined-functions.md`
- anchored types → explicit target types or table rowtype — see `skills/oracle-to-postgresql-playbook/references/sql-plsql/procedures-and-functions.md`
- RAISE_APPLICATION_ERROR → RAISE EXCEPTION ... USING ERRCODE (keep the code mapping consistent) — see `skills/oracle-to-postgresql-playbook/references/sql-plsql/procedures-and-functions.md`
- collections → arrays / SETOF composite (one RETURN NEXT per element) — see `skills/oracle-to-postgresql-playbook/references/sql-plsql/collections-and-bulk-operations.md`
- DECODE/NVL → CASE/COALESCE (NULL-safe comparison) — see `skills/oracle-to-postgresql-playbook/references/sql-plsql/single-row-and-aggregate-functions.md`

--- SOURCE (PACKAGE) — DEMO.BOOK_PKG ---
CREATE OR REPLACE EDITIONABLE PACKAGE "DEMO"."BOOK_PKG" AS
    -- Get available quantity for a book
    FUNCTION get_available_quantity(p_book_id NUMBER) RETURN NUMBER;

    -- Calculate average price for a book
    FUNCTION get_avg_price(p_book_id NUMBER) RETURN NUMBER;

    -- Check if book is in stock
    FUNCTION is_in_stock(p_book_id NUMBER) RETURN NUMBER;

    -- Get book details with inventory
    PROCEDURE get_book_details(
        p_book_id IN NUMBER,
        p_title OUT VARCHAR2,
        p_author OUT VARCHAR2,
        p_total_qty OUT NUMBER,
        p_avg_price OUT NUMBER
    );
END book_pkg;

CREATE OR REPLACE EDITIONABLE PACKAGE BODY "DEMO"."BOOK_PKG" AS
    FUNCTION get_available_quantity(p_book_id NUMBER) RETURN NUMBER IS
        v_qty listings.quantity%TYPE := 0;
    BEGIN
        SELECT NVL(SUM(quantity), 0)
        INTO v_qty
        FROM listings
        WHERE book_id = p_book_id
          AND status = 1
          AND listing_type = 'STORE';
        RETURN v_qty;
    END;

    FUNCTION get_avg_price(p_book_id NUMBER) RETURN NUMBER IS
        v_avg listings.price%TYPE := 0;
    BEGIN
        SELECT NVL(AVG(price), 0)
        INTO v_avg
        FROM listings
        WHERE book_id = p_book_id
          AND status = 1
          AND listing_type = 'STORE';
        RETURN v_avg;
    END;

    FUNCTION is_in_stock(p_book_id NUMBER) RETURN NUMBER IS
    BEGIN
        RETURN CASE WHEN get_available_quantity(p_book_id) > 0 THEN 1 ELSE 0 END;
    END;

    PROCEDURE get_book_details(
        p_book_id IN NUMBER,
        p_title OUT VARCHAR2,
        p_author OUT VARCHAR2,
        p_total_qty OUT NUMBER,
        p_avg_price OUT NUMBER
    ) IS
    BEGIN
        SELECT title, author
        INTO p_title, p_author
        FROM books
        WHERE id = p_book_id;

        p_total_qty := get_available_quantity(p_book_id);
        p_avg_price := get_avg_price(p_book_id);
    END;
END book_pkg;

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

--- SOURCE (PACKAGE) — DEMO.REPORTING_PKG ---
CREATE OR REPLACE EDITIONABLE PACKAGE "DEMO"."REPORTING_PKG" AS
    -- Get top selling books
    TYPE book_sales_rec IS RECORD (
        book_id NUMBER,
        title VARCHAR2(255),
        total_sold NUMBER,
        revenue NUMBER
    );
    TYPE book_sales_tab IS TABLE OF book_sales_rec;

    FUNCTION get_top_books(p_limit NUMBER DEFAULT 10) RETURN book_sales_tab PIPELINED;

    -- Get customer statistics
    PROCEDURE get_customer_stats(
        p_customer_id IN NUMBER,
        p_total_orders OUT NUMBER,
        p_total_spent OUT NUMBER,
        p_avg_order OUT NUMBER,
        p_last_order_date OUT DATE
    );
END reporting_pkg;

CREATE OR REPLACE EDITIONABLE PACKAGE BODY "DEMO"."REPORTING_PKG" AS
    FUNCTION get_top_books(p_limit NUMBER DEFAULT 10) RETURN book_sales_tab PIPELINED IS
        v_rec book_sales_rec;
    BEGIN
        FOR rec IN (
            SELECT b.id, b.title, 
                   SUM(oi.quantity) as total_sold,
                   SUM(oi.book_price * oi.quantity) as revenue
            FROM books b
            JOIN order_items oi ON b.id = oi.book_id
            JOIN orders o ON oi.order_id = o.id
            WHERE o.status NOT IN ('CANCELLED')
            GROUP BY b.id, b.title
            ORDER BY total_sold DESC
            FETCH FIRST p_limit ROWS ONLY
        ) LOOP
            v_rec.book_id := rec.id;
            v_rec.title := rec.title;
            v_rec.total_sold := rec.total_sold;
            v_rec.revenue := rec.revenue;
            PIPE ROW(v_rec);
        END LOOP;
    END;

    PROCEDURE get_customer_stats(
        p_customer_id IN NUMBER,
        p_total_orders OUT NUMBER,
        p_total_spent OUT NUMBER,
        p_avg_order OUT NUMBER,
        p_last_order_date OUT DATE
    ) IS
    BEGIN
        SELECT COUNT(*),
               NVL(SUM(total_amount), 0),
               NVL(AVG(total_amount), 0),
               MAX(TRUNC(created_on))
        INTO p_total_orders, p_total_spent, p_avg_order, p_last_order_date
        FROM orders
        WHERE customer_id = p_customer_id
          AND status NOT IN ('CANCELLED');
    END;
END reporting_pkg;

--- SOURCE (PACKAGE) — DEMO.VALIDATION_PKG ---
CREATE OR REPLACE EDITIONABLE PACKAGE "DEMO"."VALIDATION_PKG" AS
    -- Validate email format
    FUNCTION is_valid_email(p_email VARCHAR2) RETURN NUMBER;

    -- Validate ISBN format
    FUNCTION is_valid_isbn(p_isbn VARCHAR2) RETURN NUMBER;

    -- Validate price range
    FUNCTION is_valid_price(p_price NUMBER) RETURN NUMBER;
END validation_pkg;

CREATE OR REPLACE EDITIONABLE PACKAGE BODY "DEMO"."VALIDATION_PKG" AS
    FUNCTION is_valid_email(p_email VARCHAR2) RETURN NUMBER IS
    BEGIN
        RETURN CASE 
            WHEN REGEXP_LIKE(p_email, '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$') 
            THEN 1 
            ELSE 0 
        END;
    END;

    FUNCTION is_valid_isbn(p_isbn VARCHAR2) RETURN NUMBER IS
    BEGIN
        RETURN CASE 
            WHEN LENGTH(REGEXP_REPLACE(p_isbn, '[^0-9X]', '')) IN (10, 13) THEN 1 
            ELSE 0 
        END;
    END;

    FUNCTION is_valid_price(p_price NUMBER) RETURN NUMBER IS
    BEGIN
        RETURN CASE 
            WHEN p_price > 0 AND p_price < 10000 THEN 1 
            ELSE 0 
        END;
    END;
END validation_pkg;
