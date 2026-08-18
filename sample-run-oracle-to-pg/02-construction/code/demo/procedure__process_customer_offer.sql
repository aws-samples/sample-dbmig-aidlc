-- Converted from Oracle DEMO.PROCESS_CUSTOMER_OFFER -> PostgreSQL demo.process_customer_offer
-- Decisions:
--   SYSTIMESTAMP            -> now()  (transaction timestamp)
--   RAISE_APPLICATION_ERROR -> RAISE EXCEPTION ... USING ERRCODE
--       Oracle error -20002 is mapped to the user-defined SQLSTATE 'U0002'.
--       *** Do NOT use 'P0002' here: PostgreSQL reserves the 'P0' class for PL/pgSQL and
--       P0002 IS the built-in no_data_found. Mapping ORA-20002 onto P0002 would make an
--       application handler for "invalid action" also swallow genuine NO_DATA_FOUND errors.
--       The 'U0' class is unassigned by the standard and by PostgreSQL, so 'U000n' gives a
--       collision-free, self-documenting 1:1 mapping of the Oracle error number.
--       Ref: equivalence-spec.md §4 (mapped Oracle<->PG SQLSTATE)
--   COMMIT                  -> REMOVED (caller owns the transaction)
--   listings.status is bigint (from NUMBER(10,0)); the literal 1 / 2 assignments are unchanged.

CREATE OR REPLACE PROCEDURE demo.process_customer_offer(
    p_listing_id numeric,
    p_action     varchar,   -- 'APPROVE' or 'REJECT'
    p_admin_id   numeric,
    p_notes      varchar DEFAULT NULL
)
LANGUAGE plpgsql
AS $$
BEGIN
    IF p_action = 'APPROVE' THEN
        UPDATE demo.listings
        SET status       = 1,
            listing_type = 'STORE',
            processed_at = now(),
            processed_by = p_admin_id,
            admin_notes  = p_notes,
            updated_on   = now()
        WHERE id = p_listing_id;
    ELSIF p_action = 'REJECT' THEN
        UPDATE demo.listings
        SET status       = 2,
            processed_at = now(),
            processed_by = p_admin_id,
            admin_notes  = p_notes,
            updated_on   = now()
        WHERE id = p_listing_id;
    ELSE
        RAISE EXCEPTION 'Invalid action. Use APPROVE or REJECT'
            USING ERRCODE = 'U0002';   -- maps Oracle ORA-20002 (NOT P0002 = no_data_found)
    END IF;
END;
$$;
