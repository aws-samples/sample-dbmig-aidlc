-- DEMO.ARCHIVE_OLD_ORDERS. SYSDATE - n -> localtimestamp(0) - n days. DELETE FROM (subquery)
-- -> direct DELETE (checks/non-portable-constructs.md). DBMS_OUTPUT.PUT_LINE -> RAISE NOTICE;
-- SQL%ROWCOUNT -> GET DIAGNOSTICS. COMMIT removed: the caller owns the transaction
-- (sql-plsql/transaction-model.md), which also keeps the procedure testable in a rolled-back txn.
CREATE OR REPLACE PROCEDURE demo.archive_old_orders(p_days_old numeric DEFAULT 365)
LANGUAGE plpgsql AS $$
DECLARE
    v_cutoff_date demo.orders.created_on%TYPE;
    v_count bigint;
BEGIN
    v_cutoff_date := localtimestamp(0) - p_days_old * interval '1 day';
    DELETE FROM demo.orders
    WHERE created_on < v_cutoff_date
      AND status IN ('DELIVERED', 'CANCELLED');
    GET DIAGNOSTICS v_count = ROW_COUNT;
    RAISE NOTICE 'Orders eligible for archiving: %', v_count;
END $$;
