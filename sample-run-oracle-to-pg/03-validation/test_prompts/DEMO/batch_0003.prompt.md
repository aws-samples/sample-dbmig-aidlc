<!-- dbmig test-generation prompt  batch 3/4
     Write one test spec (YAML) per object:
       - PACKAGE DEMO.REPORTING_PKG -> tests/DEMO/package__reporting_pkg.test.yaml
       - PACKAGE DEMO.VALIDATION_PKG -> tests/DEMO/package__validation_pkg.test.yaml
       - PROCEDURE DEMO.ARCHIVE_OLD_ORDERS -> tests/DEMO/procedure__archive_old_orders.test.yaml
       - PROCEDURE DEMO.CLEAR_SHOPPING_CART -> tests/DEMO/procedure__clear_shopping_cart.test.yaml
       - PROCEDURE DEMO.GENERATE_SALES_REPORT -> tests/DEMO/procedure__generate_sales_report.test.yaml
       - PROCEDURE DEMO.PROCESS_CUSTOMER_OFFER -> tests/DEMO/procedure__process_customer_offer.test.yaml
     Then set each unit's status 'generated' in test-manifest-DEMO.yaml. -->
<!-- PARTIAL coverage REPORTING_PKG: empty referenced tables: ORDERS, ORDER_ITEMS -->
<!-- CAUTION ARCHIVE_OLD_ORDERS: manages its own transaction (COMMIT/ROLLBACK/BEGIN TRAN) — NOT safely net-effect testable via the rollback harness. Write a NON-DESTRUCTIVE case (e.g. a non-existent key) or leave 'cases: []' and note it. -->
<!-- LOW_COVERAGE ARCHIVE_OLD_ORDERS: every table it reads is EMPTY in the source (ORDERS) — cases only exercise the empty/default path; state this in `notes:`. -->
<!-- CAUTION CLEAR_SHOPPING_CART: manages its own transaction (COMMIT/ROLLBACK/BEGIN TRAN) — NOT safely net-effect testable via the rollback harness. Write a NON-DESTRUCTIVE case (e.g. a non-existent key) or leave 'cases: []' and note it. -->
<!-- LOW_COVERAGE CLEAR_SHOPPING_CART: every table it reads is EMPTY in the source (SHOPPING_CART_ITEMS) — cases only exercise the empty/default path; state this in `notes:`. -->
<!-- LOW_COVERAGE GENERATE_SALES_REPORT: every table it reads is EMPTY in the source (ORDERS) — cases only exercise the empty/default path; state this in `notes:`. -->
<!-- CAUTION PROCESS_CUSTOMER_OFFER: manages its own transaction (COMMIT/ROLLBACK/BEGIN TRAN) — NOT safely net-effect testable via the rollback harness. Write a NON-DESTRUCTIVE case (e.g. a non-existent key) or leave 'cases: []' and note it. -->

=== CONTEXT ===
Shared tests context for this run: `migrations/<project>/03-validation/_context-tests.md`. Read it once per session if you have not already — it holds the customer-specific rules (highest precedence), datatype map, engine checks and playbook index this task relies on. Do not skip it.

=== TASK — GENERATE EQUIVALENCE TESTS ===
Generate equivalence tests that prove each of the 6 converted PostgreSQL (Aurora PostgreSQL compatible) objects below (one spec file per object, as listed in the header) behaves the same as the Oracle source: same input → same return value (functions) or same net effect (procedures). Tests run on BOTH engines and the results are compared. Use the spec format and Rules in the context above.

### PACKAGE DEMO.REPORTING_PKG — write a **function and/or procedure**-shape spec
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

--- CONVERTED TARGET CODE (PostgreSQL) — use these exact routine names and signatures in target_sql / call_target ---
-- Package REPORTING_PKG (spec + body) flattened to <package>_<subprogram>.
-- PIPELINED book_sales_tab -> RETURNS TABLE + RETURN QUERY (sql-plsql/user-defined-functions.md).
-- Declared column types match the query's ACTUAL types (b.id bigint, b.title varchar,
-- SUM(bigint) numeric, SUM(numeric) numeric); a mismatch would only fail at execution.
-- FETCH FIRST n ROWS ONLY -> LIMIT. NOTE: ORDER BY total_sold DESC has no tie-breaker in the
-- source, so tied rows may come back in a different order on each engine (compare as a set).
CREATE OR REPLACE FUNCTION demo.reporting_pkg_get_top_books(p_limit numeric DEFAULT 10)
RETURNS TABLE (book_id bigint, title varchar, total_sold numeric, revenue numeric)
LANGUAGE plpgsql STABLE AS $$
BEGIN
    RETURN QUERY
    SELECT b.id, b.title::varchar,
           sum(oi.quantity)::numeric AS total_sold,
           sum(oi.book_price * oi.quantity)::numeric AS revenue
    FROM demo.books b
    JOIN demo.order_items oi ON b.id = oi.book_id
    JOIN demo.orders o ON oi.order_id = o.id
    WHERE o.status NOT IN ('CANCELLED')
    GROUP BY b.id, b.title
    ORDER BY total_sold DESC
    LIMIT p_limit;
END $$;

-- OUT params; TRUNC(created_on) -> date_trunc('day', ...) returned as timestamp(0) (Oracle DATE).
CREATE OR REPLACE PROCEDURE demo.reporting_pkg_get_customer_stats(
    p_customer_id numeric,
    OUT p_total_orders numeric,
    OUT p_total_spent numeric,
    OUT p_avg_order numeric,
    OUT p_last_order_date timestamp(0))
LANGUAGE plpgsql AS $$
BEGIN
    SELECT count(*), coalesce(sum(total_amount), 0), coalesce(avg(total_amount), 0),
           max(date_trunc('day', created_on))
    INTO p_total_orders, p_total_spent, p_avg_order, p_last_order_date
    FROM demo.orders
    WHERE customer_id = p_customer_id AND status NOT IN ('CANCELLED');
END $$;

### PACKAGE DEMO.VALIDATION_PKG — write a **function and/or procedure**-shape spec
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

--- CONVERTED TARGET CODE (PostgreSQL) — use these exact routine names and signatures in target_sql / call_target ---
-- Package VALIDATION_PKG (spec + body) flattened to <package>_<subprogram>.
-- REGEXP_LIKE -> ~ (regexp_like() is also native since PG 15). REGEXP_REPLACE replaces ALL matches
-- in Oracle; PostgreSQL needs the 'g' flag (checks/non-portable-constructs.md).
-- Oracle LENGTH('') is NULL; PostgreSQL length('') is 0. Both give 0 here (NULL IN (...) -> ELSE 0).
CREATE OR REPLACE FUNCTION demo.validation_pkg_is_valid_email(p_email varchar)
RETURNS numeric LANGUAGE plpgsql IMMUTABLE AS $$
BEGIN
    RETURN CASE WHEN p_email ~ '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$' THEN 1 ELSE 0 END;
END $$;

CREATE OR REPLACE FUNCTION demo.validation_pkg_is_valid_isbn(p_isbn varchar)
RETURNS numeric LANGUAGE plpgsql IMMUTABLE AS $$
BEGIN
    RETURN CASE WHEN length(regexp_replace(p_isbn, '[^0-9X]', '', 'g')) IN (10, 13) THEN 1 ELSE 0 END;
END $$;

CREATE OR REPLACE FUNCTION demo.validation_pkg_is_valid_price(p_price numeric)
RETURNS numeric LANGUAGE plpgsql IMMUTABLE AS $$
BEGIN
    RETURN CASE WHEN p_price > 0 AND p_price < 10000 THEN 1 ELSE 0 END;
END $$;

### PROCEDURE DEMO.ARCHIVE_OLD_ORDERS — write a **procedure**-shape spec
--- SOURCE (PROCEDURE) — DEMO.ARCHIVE_OLD_ORDERS ---
CREATE OR REPLACE EDITIONABLE PROCEDURE "DEMO"."ARCHIVE_OLD_ORDERS" (
    p_days_old IN NUMBER DEFAULT 365
) IS
    v_cutoff_date orders.created_on%TYPE;
BEGIN
    v_cutoff_date := SYSDATE - p_days_old;

    -- In a real scenario, you'd move to an archive table
    -- For demo, we'll just delete records without actual archive
    -- DELETE with subquery (causes DMS SC issue 5068)
    DELETE FROM (
        SELECT * FROM orders
        WHERE created_on < v_cutoff_date
          AND status IN ('DELIVERED', 'CANCELLED')
    );
    DBMS_OUTPUT.PUT_LINE('Orders eligible for archiving: ' || SQL%ROWCOUNT);
    COMMIT;
END;

--- CONVERTED TARGET CODE (PostgreSQL) — use these exact routine names and signatures in target_sql / call_target ---
-- DEMO.ARCHIVE_OLD_ORDERS. SYSDATE - n -> localtimestamp(0) - n days. DELETE FROM (subquery)
-- -> direct DELETE (checks/non-portable-constructs.md). DBMS_OUTPUT.PUT_LINE -> RAISE NOTICE;
-- SQL%ROWCOUNT -> GET DIAGNOSTICS. COMMIT removed: the caller owns the transaction
-- (sql-plsql/transaction-model.md), which also keeps the procedure testable in a rolled-back txn.
CREATE OR REPLACE PROCEDURE demo.archive_old_orders(p_days_old numeric DEFAULT 365)
LANGUAGE plpgsql AS $$
DECLARE
    v_cutoff_date demo.orders.created_on%TYPE;
    v_count bigint;
BEGIN
    v_cutoff_date := localtimestamp(0) - p_days_old * interval '1 day';
    DELETE FROM demo.orders
    WHERE created_on < v_cutoff_date
      AND status IN ('DELIVERED', 'CANCELLED');
    GET DIAGNOSTICS v_count = ROW_COUNT;
    RAISE NOTICE 'Orders eligible for archiving: %', v_count;
END $$;

### PROCEDURE DEMO.CLEAR_SHOPPING_CART — write a **procedure**-shape spec
--- SOURCE (PROCEDURE) — DEMO.CLEAR_SHOPPING_CART ---
CREATE OR REPLACE EDITIONABLE PROCEDURE "DEMO"."CLEAR_SHOPPING_CART" (p_customer_id IN NUMBER) IS
BEGIN
    DELETE FROM shopping_cart_items
    WHERE customer_id = p_customer_id
      AND is_wishlist_item = 0;
    COMMIT;
END;

--- CONVERTED TARGET CODE (PostgreSQL) — use these exact routine names and signatures in target_sql / call_target ---
-- DEMO.CLEAR_SHOPPING_CART. COMMIT removed (caller owns the transaction).
CREATE OR REPLACE PROCEDURE demo.clear_shopping_cart(p_customer_id numeric)
LANGUAGE plpgsql AS $$
BEGIN
    DELETE FROM demo.shopping_cart_items
    WHERE customer_id = p_customer_id
      AND is_wishlist_item = 0;
END $$;

### PROCEDURE DEMO.GENERATE_SALES_REPORT — write a **procedure**-shape spec
--- SOURCE (PROCEDURE) — DEMO.GENERATE_SALES_REPORT ---
CREATE OR REPLACE EDITIONABLE PROCEDURE "DEMO"."GENERATE_SALES_REPORT" (
    p_start_date IN DATE,
    p_end_date IN DATE,
    p_total_orders OUT NUMBER,
    p_total_revenue OUT NUMBER,
    p_avg_order_value OUT NUMBER
) IS
BEGIN
    SELECT COUNT(*),
           NVL(SUM(total_amount), 0),
           NVL(AVG(total_amount), 0)
    INTO p_total_orders, p_total_revenue, p_avg_order_value
    FROM orders
    WHERE created_on BETWEEN p_start_date AND p_end_date
      AND status NOT IN ('CANCELLED');
END;

--- CONVERTED TARGET CODE (PostgreSQL) — use these exact routine names and signatures in target_sql / call_target ---
-- DEMO.GENERATE_SALES_REPORT. OUT parameters via CREATE PROCEDURE (PG 14+, baseline: Conversion
-- defaults). DATE parameters -> timestamp(0).
CREATE OR REPLACE PROCEDURE demo.generate_sales_report(
    p_start_date timestamp(0),
    p_end_date timestamp(0),
    OUT p_total_orders numeric,
    OUT p_total_revenue numeric,
    OUT p_avg_order_value numeric)
LANGUAGE plpgsql AS $$
BEGIN
    SELECT count(*), coalesce(sum(total_amount), 0), coalesce(avg(total_amount), 0)
    INTO p_total_orders, p_total_revenue, p_avg_order_value
    FROM demo.orders
    WHERE created_on BETWEEN p_start_date AND p_end_date
      AND status NOT IN ('CANCELLED');
END $$;

### PROCEDURE DEMO.PROCESS_CUSTOMER_OFFER — write a **procedure**-shape spec
--- SOURCE (PROCEDURE) — DEMO.PROCESS_CUSTOMER_OFFER ---
CREATE OR REPLACE EDITIONABLE PROCEDURE "DEMO"."PROCESS_CUSTOMER_OFFER" (
    p_listing_id IN NUMBER,
    p_action IN VARCHAR2,  -- 'APPROVE' or 'REJECT'
    p_admin_id IN NUMBER,
    p_notes IN VARCHAR2 DEFAULT NULL
) IS
BEGIN
    IF p_action = 'APPROVE' THEN
        UPDATE listings
        SET status = 1,
            listing_type = 'STORE',
            processed_at = SYSTIMESTAMP,
            processed_by = p_admin_id,
            admin_notes = p_notes,
            updated_on = SYSTIMESTAMP
        WHERE id = p_listing_id;
    ELSIF p_action = 'REJECT' THEN
        UPDATE listings
        SET status = 2,
            processed_at = SYSTIMESTAMP,
            processed_by = p_admin_id,
            admin_notes = p_notes,
            updated_on = SYSTIMESTAMP
        WHERE id = p_listing_id;
    ELSE
        RAISE_APPLICATION_ERROR(-20002, 'Invalid action. Use APPROVE or REJECT');
    END IF;
    COMMIT;
END;

--- CONVERTED TARGET CODE (PostgreSQL) — use these exact routine names and signatures in target_sql / call_target ---
-- DEMO.PROCESS_CUSTOMER_OFFER. RAISE_APPLICATION_ERROR(-20002) -> RAISE EXCEPTION ... ERRCODE 'U0002'
-- (mapping -200nn -> 'U00nn', used consistently). SYSTIMESTAMP into a TIMESTAMP column ->
-- localtimestamp. COMMIT removed (caller owns the transaction).
CREATE OR REPLACE PROCEDURE demo.process_customer_offer(
    p_listing_id numeric,
    p_action varchar,
    p_admin_id numeric,
    p_notes varchar DEFAULT NULL)
LANGUAGE plpgsql AS $$
BEGIN
    IF p_action = 'APPROVE' THEN
        UPDATE demo.listings
        SET status = 1, listing_type = 'STORE', processed_at = localtimestamp,
            processed_by = p_admin_id, admin_notes = p_notes, updated_on = localtimestamp
        WHERE id = p_listing_id;
    ELSIF p_action = 'REJECT' THEN
        UPDATE demo.listings
        SET status = 2, processed_at = localtimestamp,
            processed_by = p_admin_id, admin_notes = p_notes, updated_on = localtimestamp
        WHERE id = p_listing_id;
    ELSE
        RAISE EXCEPTION 'Invalid action. Use APPROVE or REJECT' USING ERRCODE = 'U0002';
    END IF;
END $$;

--- SAMPLED REAL DATA (use these actual values) ---
### BOOKS  (columns: ID, TITLE, AUTHOR, ISBN, DESCRIPTION, PUBLISH_DATE, YEAR, CREATED_ON, UPDATED_ON, CREATED_BY, GENRE_ID, PUBLISHER_ID, BOOK_TYPE_ID, SEARCH_TEXT)
  30 | The Devil in the White City | Erik Larson | 9780307408846 | This gripping non-fiction narrative intertwines two remarkable stories set again… |  |  | 2026-10-30 01:53:56.839131 |  | system | 3 | 2 | 1 | the devil in the white city erik larson 9780307408846
  31 | The Nightingale | Kristin Hannah | 9780312577223 | Set in France during World War II, this powerful novel follows two sisters—one r… |  |  | 2026-10-30 01:53:56.846624 |  | system | 4 | 3 | 1 | the nightingale kristin hannah 9780312577223
  32 | A Gentleman in Moscow | Amor Towles | 9780670026197 | In 1922, Count Alexander Rostov is sentenced by a Bolshevik tribunal to house ar… |  |  | 2026-10-30 01:53:56.852888 |  | system | 4 | 4 | 2 | a gentleman in moscow amor towles 9780670026197
### LISTINGS  (columns: ID, BOOK_ID, SELLER_ID, PRICE, QUANTITY, CONDITION_ID, STATUS, LISTING_TYPE, ADMIN_NOTES, PROCESSED_AT, PROCESSED_BY, IS_FEATURED, IS_BESTSELLER, IS_NEW_ARRIVAL, CREATED_ON, UPDATED_ON)
  1 | 1 | 1 | 10.95 | 25 | 2 | 1 | SYSTEM |  |  |  | 1 | 0 | 1 | 2026-10-30 01:53:57.004066 | 
  2 | 2 | 1 | 13.95 | 3 | 3 | 1 | SYSTEM |  |  |  | 0 | 1 | 0 | 2026-10-30 01:53:57.008985 | 
  3 | 3 | 1 | 6.5 | 10 | 1 | 1 | SYSTEM |  |  |  | 1 | 1 | 0 | 2026-10-30 01:53:57.013576 | 
