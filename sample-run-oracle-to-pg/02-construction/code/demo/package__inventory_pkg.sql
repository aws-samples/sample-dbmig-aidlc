-- Package INVENTORY_PKG (spec + body) flattened to <package>_<subprogram>.
-- RAISE_APPLICATION_ERROR(-20001) -> ERRCODE 'U0001'. Caller owns the transaction.
CREATE OR REPLACE PROCEDURE demo.inventory_pkg_reduce_inventory(p_listing_id numeric, p_quantity numeric)
LANGUAGE plpgsql AS $$
DECLARE
    v_current_qty demo.listings.quantity%TYPE;
BEGIN
    SELECT quantity INTO STRICT v_current_qty FROM demo.listings WHERE id = p_listing_id FOR UPDATE;
    IF v_current_qty < p_quantity THEN
        RAISE EXCEPTION 'Insufficient inventory' USING ERRCODE = 'U0001';
    END IF;
    UPDATE demo.listings
    SET quantity = quantity - p_quantity, updated_on = localtimestamp
    WHERE id = p_listing_id;
END $$;

-- Oracle: an unhandled NO_DATA_FOUND in a function called from SQL returns NULL, so a missing
-- listing returns NULL here instead of raising.
CREATE OR REPLACE FUNCTION demo.inventory_pkg_has_sufficient_inventory(p_listing_id numeric, p_quantity numeric)
RETURNS numeric LANGUAGE plpgsql STABLE AS $$
DECLARE
    v_current_qty demo.listings.quantity%TYPE;
BEGIN
    SELECT quantity INTO v_current_qty FROM demo.listings WHERE id = p_listing_id;
    IF NOT FOUND THEN
        RETURN NULL;
    END IF;
    RETURN CASE WHEN v_current_qty >= p_quantity THEN 1 ELSE 0 END;
END $$;

CREATE OR REPLACE FUNCTION demo.inventory_pkg_get_low_stock_count(p_threshold numeric DEFAULT 5)
RETURNS numeric LANGUAGE plpgsql STABLE AS $$
DECLARE
    v_count bigint;   -- PLS_INTEGER
BEGIN
    SELECT count(*) INTO v_count
    FROM demo.listings
    WHERE status = 1 AND listing_type = 'STORE' AND quantity <= p_threshold;
    RETURN v_count;
END $$;
