-- Converted from Oracle DEMO.CALCULATE_DISCOUNT_PCT -> PostgreSQL demo.calculate_discount_pct
-- Decisions:
--   DETERMINISTIC   -> IMMUTABLE       (non-portable-constructs.md → PL/SQL → PL/pgSQL)
--   PARALLEL_ENABLE -> PARALLEL SAFE
--   NUMBER          -> numeric (exact arithmetic; ROUND(numeric, 2) is equivalent in both engines)
--   No table access, so IMMUTABLE is correct.

CREATE OR REPLACE FUNCTION demo.calculate_discount_pct(
    p_original_price   numeric,
    p_discounted_price numeric
) RETURNS numeric
LANGUAGE plpgsql
IMMUTABLE
PARALLEL SAFE
AS $$
BEGIN
    IF p_original_price = 0 THEN
        RETURN 0;
    END IF;
    RETURN round(((p_original_price - p_discounted_price) / p_original_price) * 100, 2);
END;
$$;
