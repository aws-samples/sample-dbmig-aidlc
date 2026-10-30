-- DEMO.CALCULATE_DISCOUNT_PCT. DETERMINISTIC -> IMMUTABLE, PARALLEL_ENABLE -> PARALLEL SAFE.
-- ROUND(numeric, 2) rounds half away from zero on both engines.
CREATE OR REPLACE FUNCTION demo.calculate_discount_pct(p_original_price numeric, p_discounted_price numeric)
RETURNS numeric LANGUAGE plpgsql IMMUTABLE PARALLEL SAFE AS $$
BEGIN
    IF p_original_price = 0 THEN
        RETURN 0;
    END IF;
    RETURN round(((p_original_price - p_discounted_price) / p_original_price) * 100, 2);
END $$;
