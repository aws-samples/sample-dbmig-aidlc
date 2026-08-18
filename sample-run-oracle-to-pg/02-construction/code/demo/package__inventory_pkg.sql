-- Converted from Oracle DEMO.INVENTORY_PKG (spec + body) -> PostgreSQL demo.inventory_pkg_*
-- Package flattening -> <package>_<subprogram>. Ref: checks/package-naming.md
--
-- Decisions:
--   SELECT ... FOR UPDATE   -> identical syntax in PostgreSQL (row lock retained).
--   SELECT INTO (single row) -> SELECT INTO STRICT, preserving Oracle's implicit
--       NO_DATA_FOUND when the listing does not exist.
--   RAISE_APPLICATION_ERROR(-20001, ...) -> RAISE EXCEPTION ... USING ERRCODE = 'U0001'
--       Oracle ORA-20001 maps to the user-defined SQLSTATE 'U0001'. The 'P0' class is
--       AVOIDED on purpose: PostgreSQL reserves it for PL/pgSQL (P0001 raise_exception,
--       P0002 no_data_found, P0003 too_many_rows), so reusing it would make application
--       error handlers ambiguous. 'U0' is unassigned, giving a collision-free 1:1 mapping
--       of the Oracle error number.
--   SYSTIMESTAMP -> now();  PLS_INTEGER -> bigint.
--   reduce_inventory had NO COMMIT in the source — nothing to remove; the caller owns the txn.

CREATE OR REPLACE PROCEDURE demo.inventory_pkg_reduce_inventory(
    p_listing_id numeric,
    p_quantity   numeric
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_current_qty demo.listings.quantity%TYPE;
BEGIN
    SELECT quantity INTO STRICT v_current_qty
    FROM demo.listings
    WHERE id = p_listing_id
    FOR UPDATE;

    IF v_current_qty < p_quantity THEN
        RAISE EXCEPTION 'Insufficient inventory'
            USING ERRCODE = 'U0001';   -- maps Oracle ORA-20001
    END IF;

    UPDATE demo.listings
    SET quantity   = quantity - p_quantity,
        updated_on = now()
    WHERE id = p_listing_id;
END;
$$;

CREATE OR REPLACE FUNCTION demo.inventory_pkg_has_sufficient_inventory(
    p_listing_id numeric,
    p_quantity   numeric
) RETURNS numeric
LANGUAGE plpgsql
STABLE
AS $$
DECLARE
    v_current_qty demo.listings.quantity%TYPE;
BEGIN
    SELECT quantity INTO STRICT v_current_qty
    FROM demo.listings
    WHERE id = p_listing_id;

    RETURN CASE WHEN v_current_qty >= p_quantity THEN 1 ELSE 0 END;
END;
$$;

CREATE OR REPLACE FUNCTION demo.inventory_pkg_get_low_stock_count(p_threshold numeric DEFAULT 5)
RETURNS numeric
LANGUAGE plpgsql
STABLE
AS $$
DECLARE
    v_count bigint;
BEGIN
    SELECT count(*)
    INTO v_count
    FROM demo.listings
    WHERE status = 1
      AND listing_type = 'STORE'
      AND quantity <= p_threshold;
    RETURN v_count;
END;
$$;
