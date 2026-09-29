<!-- dbmig code conversion prompt
     batch: 1/3
     Convert each object and SAVE PostgreSQL code to its output file:
       - FUNCTION DEMO.CALCULATE_DISCOUNT_PCT -> code/demo/function__calculate_discount_pct.sql
       - FUNCTION DEMO.GET_CONDITION_NAME -> code/demo/function__get_condition_name.sql
       - FUNCTION DEMO.GET_CUSTOMER_FULL_NAME -> code/demo/function__get_customer_full_name.sql
       - FUNCTION DEMO.GET_CUSTOMER_LIFETIME_VALUE -> code/demo/function__get_customer_lifetime_value.sql
       - FUNCTION DEMO.GET_GENRE_NAME -> code/demo/function__get_genre_name.sql
     Then set each unit's status to 'converted' in code-manifest-DEMO.yaml. -->

=== CONTEXT ===
Shared code context for this run: `migrations/<project>/02-construction/_context-code.md`. Read it once per session if you have not already — it holds the customer-specific rules (highest precedence), datatype map, engine checks and playbook index this task relies on. Do not skip it.

=== TASK ===
Convert the following Oracle stored code object to PostgreSQL (procedural SQL — e.g. PL/pgSQL). Return only valid PostgreSQL, ready to execute. Packages/modules have no direct equivalent: map each routine to its own function/procedure. Note any construct that needs human review in a SQL comment. Qualify every created object with the target schema `demo` (derived from the source schema — do NOT use the connection's database/catalog name for qualification). Each object below is independent: convert each one and save it to its own output file (listed in the header).

=== CONSTRUCTS DETECTED IN THIS OBJECT (apply the matching guidance in the context) ===
- anchored types → explicit target types or table rowtype
- DECODE/NVL → CASE/COALESCE (NULL-safe comparison)

--- SOURCE (FUNCTION) — DEMO.CALCULATE_DISCOUNT_PCT ---
CREATE OR REPLACE EDITIONABLE FUNCTION "DEMO"."CALCULATE_DISCOUNT_PCT" (
    p_original_price NUMBER,
    p_discounted_price NUMBER
) RETURN NUMBER 
DETERMINISTIC
PARALLEL_ENABLE
IS
BEGIN
    IF p_original_price = 0 THEN
        RETURN 0;
    END IF;
    RETURN ROUND(((p_original_price - p_discounted_price) / p_original_price) * 100, 2);
END;

--- SOURCE (FUNCTION) — DEMO.GET_CONDITION_NAME ---
CREATE OR REPLACE EDITIONABLE FUNCTION "DEMO"."GET_CONDITION_NAME" (p_condition_id NUMBER)
RETURN VARCHAR2 IS
    v_name conditions.name%TYPE;
BEGIN
    SELECT name INTO v_name
    FROM conditions
    WHERE id = p_condition_id;
    RETURN v_name;
EXCEPTION
    WHEN NO_DATA_FOUND THEN
        RETURN 'Unknown';
END;

--- SOURCE (FUNCTION) — DEMO.GET_CUSTOMER_FULL_NAME ---
CREATE OR REPLACE EDITIONABLE FUNCTION "DEMO"."GET_CUSTOMER_FULL_NAME" (p_customer_id NUMBER)
RETURN VARCHAR2 IS
    v_name VARCHAR2(500);
BEGIN
    SELECT first_name || ' ' || last_name
    INTO v_name
    FROM customers
    WHERE id = p_customer_id;
    RETURN v_name;
EXCEPTION
    WHEN NO_DATA_FOUND THEN
        RETURN 'Unknown Customer';
END;

--- SOURCE (FUNCTION) — DEMO.GET_CUSTOMER_LIFETIME_VALUE ---
CREATE OR REPLACE EDITIONABLE FUNCTION "DEMO"."GET_CUSTOMER_LIFETIME_VALUE" (p_customer_id NUMBER)
RETURN NUMBER IS
    v_total NUMBER := 0;
BEGIN
    SELECT NVL(SUM(total_amount), 0)
    INTO v_total
    FROM orders
    WHERE customer_id = p_customer_id
      AND status NOT IN ('CANCELLED');
    RETURN v_total;
END;

--- SOURCE (FUNCTION) — DEMO.GET_GENRE_NAME ---
CREATE OR REPLACE EDITIONABLE FUNCTION "DEMO"."GET_GENRE_NAME" (p_genre_id NUMBER)
RETURN VARCHAR2 IS
    v_name genres.name%TYPE;
BEGIN
    SELECT name INTO v_name
    FROM genres
    WHERE id = p_genre_id;
    RETURN v_name;
EXCEPTION
    WHEN NO_DATA_FOUND THEN
        RETURN 'Unknown';
END;
