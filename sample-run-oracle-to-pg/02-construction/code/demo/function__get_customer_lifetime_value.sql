-- DEMO.GET_CUSTOMER_LIFETIME_VALUE -> demo.get_customer_lifetime_value
-- NVL -> COALESCE. Aggregate always returns a row, so no NO_DATA_FOUND handling needed.
CREATE OR REPLACE FUNCTION demo.get_customer_lifetime_value(p_customer_id bigint)
RETURNS numeric
AS $$
DECLARE
  v_total numeric := 0;
BEGIN
  SELECT COALESCE(SUM(total_amount), 0) INTO v_total
  FROM demo.orders
  WHERE customer_id = p_customer_id
    AND status NOT IN ('CANCELLED');
  RETURN v_total;
END;
$$ LANGUAGE plpgsql;
