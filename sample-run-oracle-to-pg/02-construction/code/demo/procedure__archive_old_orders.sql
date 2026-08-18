-- Converted from Oracle DEMO.ARCHIVE_OLD_ORDERS -> PostgreSQL demo.archive_old_orders
-- Decisions:
--   DELETE FROM (subquery)  -> direct DELETE FROM demo.orders WHERE ...
--       Oracle's inline-view delete has no PostgreSQL equivalent (and was the documented
--       DMS SC 5068 issue). Ref: non-portable-constructs.md → DELETE FROM (subquery)
--   SYSDATE - p_days_old    -> now() - make_interval(days => ...)
--       Oracle DATE arithmetic subtracts whole days; PostgreSQL requires an interval.
--       Ref: equivalence-spec.md §6 (DATE arithmetic)
--   DBMS_OUTPUT.PUT_LINE    -> RAISE NOTICE
--   SQL%ROWCOUNT            -> GET DIAGNOSTICS v_rows = ROW_COUNT
--   COMMIT                  -> REMOVED: the caller owns the transaction (PostgreSQL idiom),
--       which is also required for the equivalence harness to roll the test back.
--       Ref: non-portable-constructs.md → Transactions in procedures

CREATE OR REPLACE PROCEDURE demo.archive_old_orders(p_days_old numeric DEFAULT 365)
LANGUAGE plpgsql
AS $$
DECLARE
    v_cutoff_date demo.orders.created_on%TYPE;
    v_rows        bigint;
BEGIN
    v_cutoff_date := now() - make_interval(days => p_days_old::int);

    -- In a real scenario, you'd move to an archive table.
    -- For demo, we delete the eligible records without an actual archive.
    DELETE FROM demo.orders
    WHERE created_on < v_cutoff_date
      AND status IN ('DELIVERED', 'CANCELLED');

    GET DIAGNOSTICS v_rows = ROW_COUNT;
    RAISE NOTICE 'Orders eligible for archiving: %', v_rows;
END;
$$;
