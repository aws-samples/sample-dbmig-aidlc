<!-- dbmig test-generation prompt  batch 1/4
     Write one test spec (YAML) per object:
       - FUNCTION DEMO.CALCULATE_DISCOUNT_PCT -> tests/DEMO/function__calculate_discount_pct.test.yaml
       - FUNCTION DEMO.GET_CONDITION_NAME -> tests/DEMO/function__get_condition_name.test.yaml
       - FUNCTION DEMO.GET_CUSTOMER_FULL_NAME -> tests/DEMO/function__get_customer_full_name.test.yaml
       - FUNCTION DEMO.GET_CUSTOMER_LIFETIME_VALUE -> tests/DEMO/function__get_customer_lifetime_value.test.yaml
       - FUNCTION DEMO.GET_GENRE_NAME -> tests/DEMO/function__get_genre_name.test.yaml
       - PACKAGE DEMO.BOOK_PKG -> tests/DEMO/package__book_pkg.test.yaml
     Then set each unit's status 'generated' in test-manifest-DEMO.yaml. -->
<!-- LOW_COVERAGE GET_CUSTOMER_LIFETIME_VALUE: every table it reads is EMPTY in the source (ORDERS) — cases only exercise the empty/default path; state this in `notes:`. -->

=== CONTEXT ===
Shared tests context for this run: `migrations/<project>/03-validation/_context-tests.md`. Read it once per session if you have not already — it holds the customer-specific rules (highest precedence), datatype map, engine checks and playbook index this task relies on. Do not skip it.

=== TASK — GENERATE EQUIVALENCE TESTS ===
Generate equivalence tests that prove each of the 6 converted PostgreSQL (Aurora PostgreSQL compatible) objects below (one spec file per object, as listed in the header) behaves the same as the Oracle source: same input → same return value (functions) or same net effect (procedures). Tests run on BOTH engines and the results are compared. Use the spec format and Rules in the context above.

### FUNCTION DEMO.CALCULATE_DISCOUNT_PCT — write a **function**-shape spec
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

--- CONVERTED TARGET CODE (PostgreSQL) — use these exact routine names and signatures in target_sql / call_target ---
-- DETERMINISTIC -> IMMUTABLE; PARALLEL_ENABLE -> PARALLEL SAFE
CREATE OR REPLACE FUNCTION demo.calculate_discount_pct(p_original_price numeric, p_discounted_price numeric)
RETURNS numeric LANGUAGE plpgsql IMMUTABLE PARALLEL SAFE AS $$
BEGIN
    IF p_original_price = 0 THEN
        RETURN 0;
    END IF;
    RETURN round(((p_original_price - p_discounted_price) / p_original_price) * 100, 2);
END $$;

### FUNCTION DEMO.GET_CONDITION_NAME — write a **function**-shape spec
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

--- CONVERTED TARGET CODE (PostgreSQL) — use these exact routine names and signatures in target_sql / call_target ---
CREATE OR REPLACE FUNCTION demo.get_condition_name(p_condition_id numeric)
RETURNS varchar LANGUAGE plpgsql STABLE AS $$
DECLARE
    v_name demo.conditions.name%TYPE;
BEGIN
    SELECT name INTO STRICT v_name FROM demo.conditions WHERE id = p_condition_id;   -- STRICT: keep Oracle NO_DATA_FOUND
    RETURN v_name;
EXCEPTION
    WHEN NO_DATA_FOUND THEN
        RETURN 'Unknown';
END $$;

### FUNCTION DEMO.GET_CUSTOMER_FULL_NAME — write a **function**-shape spec
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

--- CONVERTED TARGET CODE (PostgreSQL) — use these exact routine names and signatures in target_sql / call_target ---
CREATE OR REPLACE FUNCTION demo.get_customer_full_name(p_customer_id numeric)
RETURNS varchar LANGUAGE plpgsql STABLE AS $$
DECLARE
    v_name varchar(500);
BEGIN
    -- Oracle '||' treats NULL as ''; PostgreSQL propagates NULL -> coalesce operands
    SELECT coalesce(first_name, '') || ' ' || coalesce(last_name, '')
    INTO STRICT v_name
    FROM demo.customers WHERE id = p_customer_id;
    RETURN v_name;
EXCEPTION
    WHEN NO_DATA_FOUND THEN
        RETURN 'Unknown Customer';
END $$;

### FUNCTION DEMO.GET_CUSTOMER_LIFETIME_VALUE — write a **function**-shape spec
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

--- CONVERTED TARGET CODE (PostgreSQL) — use these exact routine names and signatures in target_sql / call_target ---
CREATE OR REPLACE FUNCTION demo.get_customer_lifetime_value(p_customer_id numeric)
RETURNS numeric LANGUAGE plpgsql STABLE AS $$
DECLARE
    v_total numeric := 0;
BEGIN
    SELECT coalesce(sum(total_amount), 0) INTO v_total
    FROM demo.orders
    WHERE customer_id = p_customer_id AND status NOT IN ('CANCELLED');
    RETURN v_total;
END $$;

### FUNCTION DEMO.GET_GENRE_NAME — write a **function**-shape spec
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

--- CONVERTED TARGET CODE (PostgreSQL) — use these exact routine names and signatures in target_sql / call_target ---
CREATE OR REPLACE FUNCTION demo.get_genre_name(p_genre_id numeric)
RETURNS varchar LANGUAGE plpgsql STABLE AS $$
DECLARE
    v_name demo.genres.name%TYPE;
BEGIN
    SELECT name INTO STRICT v_name FROM demo.genres WHERE id = p_genre_id;   -- STRICT: keep Oracle NO_DATA_FOUND
    RETURN v_name;
EXCEPTION
    WHEN NO_DATA_FOUND THEN
        RETURN 'Unknown';
END $$;

### PACKAGE DEMO.BOOK_PKG — write a **function and/or procedure**-shape spec
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

--- CONVERTED TARGET CODE (PostgreSQL) — use these exact routine names and signatures in target_sql / call_target ---
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

--- SAMPLED REAL DATA (use these actual values) ---
### CONDITIONS  (columns: ID, CREATED_ON, DESCRIPTION, NAME, UPDATED_ON)
  1 |  | Brand new, never used, in perfect condition | New | 
  2 |  | Looks new but may have been read once or twice | Like New | 
  3 |  | Shows some signs of wear, may have markings | Good | 
### CUSTOMERS  (columns: ID, USERNAME, EMAIL, FIRST_NAME, LAST_NAME, PHONE_NUMBER, PASSWORD_HASH, SUB, DATE_OF_BIRTH, CREATED_ON, EMAIL_VERIFIED, ROLE, ACCOUNT_EXPIRED, CREDENTIALS_EXPIRED, ACCOUNT_LOCKED, LAST_LOGIN)
  1 | admin | admin@bobsusedbooks.com | Admin | User | 555-999-8888 | <redacted> |  | 1980-01-01 00:00:00 | 2026-09-28 02:05:25.721450 | 1 | ADMIN | 0 | 0 | 0 | 
  2 | johndoe | john.doe@example.com | John | Doe | 555-123-4567 | <redacted> | auth0|123456 | 1985-05-15 00:00:00 | 2026-09-28 02:05:25.734726 | 1 | USER | 0 | 0 | 0 | 
  3 | janedoe | jane.doe@example.com | Jane | Doe | 555-234-5678 | <redacted> | auth0|234567 | 1990-10-20 00:00:00 | 2026-09-28 02:05:25.746187 | 1 | USER | 0 | 0 | 0 | 
### GENRES  (columns: ID, CREATED_ON, DESCRIPTION, NAME, UPDATED_ON)
  1 |  | Non-fiction account of someone's life | Biographies | 
  2 |  | Books for children | Children's Books | 
  3 |  | Non-fiction about past events | History | 
### BOOKS  (columns: ID, TITLE, AUTHOR, ISBN, DESCRIPTION, PUBLISH_DATE, YEAR, CREATED_ON, UPDATED_ON, CREATED_BY, GENRE_ID, PUBLISHER_ID, BOOK_TYPE_ID, SEARCH_TEXT)
  43 | The Night Circus | Erin Morgenstern | 9780385534635 | The circus arrives without warning, appearing at night and open only from sunset… |  |  | 2026-09-28 02:05:26.136606 |  | system | 6 | 5 | 1 | the night circus erin morgenstern 9780385534635
  44 | Mexican Gothic | Silvia Moreno-Garcia | 9780525620785 | When socialite Noemí receives a frantic letter from her newly-wed cousin begging… |  |  | 2026-09-28 02:05:26.143074 |  | system | 6 | 6 | 2 | mexican gothic silvia moreno-garcia 9780525620785
  45 | A Darker Shade of Magic | V.E. Schwab | 9780765387561 | Kell is one of the last Antari—magicians with the rare ability to travel between… |  |  | 2026-09-28 02:05:26.149371 |  | system | 6 | 7 | 1 | a darker shade of magic v.e. schwab 9780765387561
### LISTINGS  (columns: ID, BOOK_ID, SELLER_ID, PRICE, QUANTITY, CONDITION_ID, STATUS, LISTING_TYPE, ADMIN_NOTES, PROCESSED_AT, PROCESSED_BY, IS_FEATURED, IS_BESTSELLER, IS_NEW_ARRIVAL, CREATED_ON, UPDATED_ON)
  1 | 1 | 1 | 10.95 | 25 | 2 | 1 | SYSTEM |  |  |  | 1 | 0 | 1 | 2026-09-28 02:05:26.204692 | 
  2 | 2 | 1 | 13.95 | 3 | 3 | 1 | SYSTEM |  |  |  | 0 | 1 | 0 | 2026-09-28 02:05:26.208513 | 
  3 | 3 | 1 | 6.5 | 10 | 1 | 1 | SYSTEM |  |  |  | 1 | 1 | 0 | 2026-09-28 02:05:26.212295 | 
