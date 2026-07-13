-- DEMO.CALCULATE_DISCOUNT_PCT -> demo.calculate_discount_pct
-- DETERMINISTIC -> IMMUTABLE; PARALLEL_ENABLE -> PARALLEL SAFE.
CREATE OR REPLACE FUNCTION demo.calculate_discount_pct(
    p_original_price numeric,
    p_discounted_price numeric)
RETURNS numeric
IMMUTABLE PARALLEL SAFE
AS $$
BEGIN
  IF p_original_price = 0 THEN
    RETURN 0;
  END IF;
  RETURN round(((p_original_price - p_discounted_price) / p_original_price) * 100, 2);
END;
$$ LANGUAGE plpgsql;
