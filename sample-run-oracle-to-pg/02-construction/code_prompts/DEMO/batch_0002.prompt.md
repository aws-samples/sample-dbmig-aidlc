<!-- dbmig code conversion prompt
     batch: 2/3
     Convert each object and SAVE PostgreSQL code to its output file:
       - PROCEDURE DEMO.ARCHIVE_OLD_ORDERS -> code/demo/procedure__archive_old_orders.sql
       - PROCEDURE DEMO.CLEAR_SHOPPING_CART -> code/demo/procedure__clear_shopping_cart.sql
       - PROCEDURE DEMO.GENERATE_SALES_REPORT -> code/demo/procedure__generate_sales_report.sql
       - PROCEDURE DEMO.PROCESS_CUSTOMER_OFFER -> code/demo/procedure__process_customer_offer.sql
       - PROCEDURE DEMO.SET_BOOK_FEATURED -> code/demo/procedure__set_book_featured.sql
     Then set each unit's status to 'converted' in code-manifest-DEMO.yaml. -->

=== CONTEXT ===
Shared code context for this run: `migrations/<project>/02-construction/_context-code.md`. Read it once per session if you have not already — it holds the customer-specific rules (highest precedence), datatype map, engine checks and playbook index this task relies on. Do not skip it.

=== TASK ===
Convert the following Oracle stored code object to PostgreSQL (procedural SQL — e.g. PL/pgSQL). Return only valid PostgreSQL, ready to execute. Packages/modules have no direct equivalent: map each routine to its own function/procedure. Note any construct that needs human review in a SQL comment. Qualify every created object with the target schema `demo` (derived from the source schema — do NOT use the connection's database/catalog name for qualification). Each object below is independent: convert each one and save it to its own output file (listed in the header).

=== CONSTRUCTS DETECTED IN THIS OBJECT (apply the matching guidance in the context) ===
- anchored types → explicit target types or table rowtype
- Oracle-supplied package call → playbook special-features / orafce
- RAISE_APPLICATION_ERROR → RAISE EXCEPTION ... USING ERRCODE (keep the code mapping consistent)
- transaction control inside code → procedure (not function); caller owns the txn
- DECODE/NVL → CASE/COALESCE (NULL-safe comparison)

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

--- SOURCE (PROCEDURE) — DEMO.CLEAR_SHOPPING_CART ---
CREATE OR REPLACE EDITIONABLE PROCEDURE "DEMO"."CLEAR_SHOPPING_CART" (p_customer_id IN NUMBER) IS
BEGIN
    DELETE FROM shopping_cart_items
    WHERE customer_id = p_customer_id
      AND is_wishlist_item = 0;
    COMMIT;
END;

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

--- SOURCE (PROCEDURE) — DEMO.SET_BOOK_FEATURED ---
CREATE OR REPLACE EDITIONABLE PROCEDURE "DEMO"."SET_BOOK_FEATURED" (
    p_book_id IN NUMBER,
    p_is_featured IN NUMBER
) IS
BEGIN
    UPDATE listings
    SET is_featured = p_is_featured,
        updated_on = SYSTIMESTAMP
    WHERE book_id = p_book_id
      AND listing_type = 'STORE'
      AND status = 1;
    COMMIT;
END;
