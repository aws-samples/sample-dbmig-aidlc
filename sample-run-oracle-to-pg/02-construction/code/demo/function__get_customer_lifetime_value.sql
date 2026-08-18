-- Converted from Oracle DEMO.GET_CUSTOMER_LIFETIME_VALUE -> PostgreSQL demo.get_customer_lifetime_value
-- Decisions:
--   NVL -> COALESCE.
--   Plain SELECT INTO (no STRICT): the source has no NO_DATA_FOUND handler and an
--   aggregate query always returns exactly one row, so Oracle never raised it here.
--   Reads a table -> STABLE.

CREATE OR REPLACE FUNCTION demo.get_customer_lifetime_value(p_customer_id numeric)
RETURNS numeric
LANGUAGE plpgsql
STABLE
AS $$
DECLARE
    v_total numeric := 0;
BEGIN
    SELECT coalesce(sum(total_amount), 0)
    INTO v_total
    FROM demo.orders
    WHERE customer_id = p_customer_id
      AND status NOT IN ('CANCELLED');
    RETURN v_total;
END;
$$;
