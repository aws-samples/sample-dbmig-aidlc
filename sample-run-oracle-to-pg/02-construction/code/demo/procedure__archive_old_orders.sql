-- DEMO.ARCHIVE_OLD_ORDERS -> demo.archive_old_orders
-- SYSDATE - N -> now() - interval; Oracle DELETE FROM (subquery) flattened to a direct DELETE;
-- DBMS_OUTPUT.PUT_LINE + SQL%ROWCOUNT -> RAISE NOTICE + GET DIAGNOSTICS. COMMIT dropped (caller controls txn).
CREATE OR REPLACE PROCEDURE demo.archive_old_orders(p_days_old numeric DEFAULT 365)
AS $$
DECLARE
  v_cutoff_date demo.orders.created_on%TYPE;
  v_rowcount    integer;
BEGIN
  v_cutoff_date := now() - (p_days_old || ' days')::interval;
  DELETE FROM demo.orders
   WHERE created_on < v_cutoff_date
     AND status IN ('DELIVERED', 'CANCELLED');
  GET DIAGNOSTICS v_rowcount = ROW_COUNT;
  RAISE NOTICE 'Orders eligible for archiving: %', v_rowcount;
END;
$$ LANGUAGE plpgsql;
