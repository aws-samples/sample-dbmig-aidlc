<!-- dbmig test-generation prompt  batch 4/4
     Write one test spec (YAML) per object:
       - PROCEDURE DEMO.SET_BOOK_FEATURED -> tests/DEMO/procedure__set_book_featured.test.yaml
     Then set each unit's status 'generated' in test-manifest-DEMO.yaml. -->
<!-- CAUTION SET_BOOK_FEATURED: manages its own transaction (COMMIT/ROLLBACK/BEGIN TRAN) — NOT safely net-effect testable via the rollback harness. Write a NON-DESTRUCTIVE case (e.g. a non-existent key) or leave 'cases: []' and note it. -->

=== CONTEXT ===
Shared tests context for this run: `migrations/<project>/03-validation/_context-tests.md`. Read it once per session if you have not already — it holds the customer-specific rules (highest precedence), datatype map, engine checks and playbook index this task relies on. Do not skip it.

=== TASK — GENERATE EQUIVALENCE TESTS ===
Generate equivalence tests that prove the converted PostgreSQL (Aurora PostgreSQL compatible) procedure `DEMO.SET_BOOK_FEATURED` behaves the same as the Oracle source: same input → same return value (functions) or same net effect (procedures). Tests run on BOTH engines and the results are compared. Use the spec format and Rules in the context above.

### PROCEDURE DEMO.SET_BOOK_FEATURED — write a **procedure**-shape spec
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

--- CONVERTED TARGET CODE (PostgreSQL) — use these exact routine names and signatures in target_sql / call_target ---
-- COMMIT removed: caller owns the transaction.
CREATE OR REPLACE PROCEDURE demo.set_book_featured(p_book_id numeric, p_is_featured numeric)
LANGUAGE plpgsql AS $$
BEGIN
    UPDATE demo.listings
    SET is_featured = p_is_featured, updated_on = current_timestamp
    WHERE book_id = p_book_id AND listing_type = 'STORE' AND status = 1;
END $$;

--- SAMPLED REAL DATA (use these actual values) ---
### LISTINGS  (columns: ID, BOOK_ID, SELLER_ID, PRICE, QUANTITY, CONDITION_ID, STATUS, LISTING_TYPE, ADMIN_NOTES, PROCESSED_AT, PROCESSED_BY, IS_FEATURED, IS_BESTSELLER, IS_NEW_ARRIVAL, CREATED_ON, UPDATED_ON)
  1 | 1 | 1 | 10.95 | 25 | 2 | 1 | SYSTEM |  |  |  | 1 | 0 | 1 | 2026-09-28 02:05:26.204692 | 
  2 | 2 | 1 | 13.95 | 3 | 3 | 1 | SYSTEM |  |  |  | 0 | 1 | 0 | 2026-09-28 02:05:26.208513 | 
  3 | 3 | 1 | 6.5 | 10 | 1 | 1 | SYSTEM |  |  |  | 1 | 1 | 0 | 2026-09-28 02:05:26.212295 | 
