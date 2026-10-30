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
