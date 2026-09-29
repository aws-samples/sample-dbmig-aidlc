-- #RefundRequests temp table -> data-modifying CTE: the key set is read once (same snapshot) and
-- used by both the UPDATE and the INSERT, exactly as the temp table was. @@ROWCOUNT after the
-- INSERT -> GET DIAGNOSTICS. GETDATE() -> localtimestamp. CAST(x AS NVARCHAR(20)) -> x::varchar(20).
CREATE OR REPLACE PROCEDURE dbo.uspprocessrefunds()
LANGUAGE plpgsql AS $$
DECLARE
    v_refundcount integer := 0;
    v_maxid integer;
BEGIN
    SELECT max(ticketid) INTO v_maxid FROM dbo.coupons;
    WITH r AS (
        SELECT orderid, customerid, totalamount FROM dbo.shopping WHERE trim(status) = 'Refund Requested'
    ), u AS (
        UPDATE dbo.shopping o SET status = 'Refunded' FROM r WHERE o.orderid = r.orderid
    )
    INSERT INTO dbo.coupons (ticketid, customerid, orderid, issuedescription, createddate, status)
    SELECT v_maxid + row_number() OVER (ORDER BY orderid), customerid, orderid,
           'Refund processed for $' || totalamount::varchar(20), localtimestamp, 'Closed'
    FROM r;
    GET DIAGNOSTICS v_refundcount = ROW_COUNT;
    RAISE NOTICE 'Processed % refunds.', v_refundcount;
END $$;
