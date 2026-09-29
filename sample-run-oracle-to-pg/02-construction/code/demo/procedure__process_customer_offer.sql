-- COMMIT removed: caller owns the transaction.
-- RAISE_APPLICATION_ERROR(-20002) -> RAISE EXCEPTION ... ERRCODE 'U0002' (framework maps ORA-200nn -> U00nn).
CREATE OR REPLACE PROCEDURE demo.process_customer_offer(
    p_listing_id numeric, p_action varchar, p_admin_id numeric, p_notes varchar DEFAULT NULL)
LANGUAGE plpgsql AS $$
BEGIN
    IF p_action = 'APPROVE' THEN
        UPDATE demo.listings
        SET status = 1, listing_type = 'STORE', processed_at = current_timestamp,
            processed_by = p_admin_id, admin_notes = p_notes, updated_on = current_timestamp
        WHERE id = p_listing_id;
    ELSIF p_action = 'REJECT' THEN
        UPDATE demo.listings
        SET status = 2, processed_at = current_timestamp,
            processed_by = p_admin_id, admin_notes = p_notes, updated_on = current_timestamp
        WHERE id = p_listing_id;
    ELSE
        RAISE EXCEPTION 'Invalid action. Use APPROVE or REJECT' USING ERRCODE = 'U0002';
    END IF;
END $$;
