-- DEMO.INVENTORY_PKG (package body) -> flattened routines demo.inventory_pkg_*
-- SELECT ... FOR UPDATE preserved; RAISE_APPLICATION_ERROR -> RAISE EXCEPTION; SYSTIMESTAMP -> now().

CREATE OR REPLACE PROCEDURE demo.inventory_pkg_reduce_inventory(
    p_listing_id bigint,
    p_quantity   numeric)
AS $$
DECLARE
  v_current_qty demo.listings.quantity%TYPE;
BEGIN
  SELECT quantity INTO STRICT v_current_qty
  FROM demo.listings
  WHERE id = p_listing_id
  FOR UPDATE;

  IF v_current_qty < p_quantity THEN
    RAISE EXCEPTION 'Insufficient inventory';
  END IF;

  UPDATE demo.listings
     SET quantity = quantity - p_quantity,
         updated_on = now()
   WHERE id = p_listing_id;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION demo.inventory_pkg_has_sufficient_inventory(
    p_listing_id bigint,
    p_quantity   numeric)
RETURNS numeric
AS $$
DECLARE
  v_current_qty demo.listings.quantity%TYPE;
BEGIN
  SELECT quantity INTO STRICT v_current_qty
  FROM demo.listings WHERE id = p_listing_id;
  RETURN CASE WHEN v_current_qty >= p_quantity THEN 1 ELSE 0 END;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION demo.inventory_pkg_get_low_stock_count(p_threshold numeric DEFAULT 5)
RETURNS numeric
AS $$
DECLARE
  v_count integer;
BEGIN
  SELECT COUNT(*) INTO v_count
  FROM demo.listings
  WHERE status = 1 AND listing_type = 'STORE' AND quantity <= p_threshold;
  RETURN v_count;
END;
$$ LANGUAGE plpgsql;
