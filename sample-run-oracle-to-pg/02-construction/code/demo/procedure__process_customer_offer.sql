-- DEMO.PROCESS_CUSTOMER_OFFER -> demo.process_customer_offer
-- SYSTIMESTAMP -> now(); RAISE_APPLICATION_ERROR -> RAISE EXCEPTION. COMMIT dropped (caller controls txn).
CREATE OR REPLACE PROCEDURE demo.process_customer_offer(
    p_listing_id bigint,
    p_action     varchar,
    p_admin_id   bigint,
    p_notes      varchar DEFAULT NULL)
AS $$
BEGIN
  IF p_action = 'APPROVE' THEN
    UPDATE demo.listings
       SET status = 1, listing_type = 'STORE', processed_at = now(),
           processed_by = p_admin_id, admin_notes = p_notes, updated_on = now()
     WHERE id = p_listing_id;
  ELSIF p_action = 'REJECT' THEN
    UPDATE demo.listings
       SET status = 2, processed_at = now(),
           processed_by = p_admin_id, admin_notes = p_notes, updated_on = now()
     WHERE id = p_listing_id;
  ELSE
    RAISE EXCEPTION 'Invalid action. Use APPROVE or REJECT';
  END IF;
END;
$$ LANGUAGE plpgsql;
