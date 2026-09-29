-- COMMIT removed: caller owns the transaction (PostgreSQL idiom; keeps the rollback test harness valid).
-- Oracle DELETE FROM (subquery) -> direct DELETE. SYSDATE - n (days) -> localtimestamp(0) - n days.
CREATE OR REPLACE PROCEDURE demo.archive_old_orders(p_days_old numeric DEFAULT 365)
LANGUAGE plpgsql AS $$
DECLARE
    v_cutoff_date timestamp(6);
    v_count bigint;
BEGIN
    v_cutoff_date := localtimestamp(0) - p_days_old * interval '1 day';
    DELETE FROM demo.orders
    WHERE created_on < v_cutoff_date AND status IN ('DELIVERED', 'CANCELLED');
    GET DIAGNOSTICS v_count = ROW_COUNT;
    RAISE NOTICE 'Orders eligible for archiving: %', v_count;
END $$;
