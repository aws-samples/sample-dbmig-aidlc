-- #temp table -> set-based DELETE (the temp table only staged the key set).
-- DATEADD(DAY, -n, GETDATE()) -> localtimestamp - n days. PRINT -> RAISE NOTICE.
CREATE OR REPLACE PROCEDURE dbo.uspdeleteoldcoupons(p_daysold integer)
LANGUAGE plpgsql AS $$
DECLARE
    v_deleted integer := 0;
BEGIN
    DELETE FROM dbo.coupons
    WHERE trim(status) = 'Closed' AND resolveddate <= localtimestamp - p_daysold * interval '1 day';
    GET DIAGNOSTICS v_deleted = ROW_COUNT;
    IF v_deleted > 0 THEN
        RAISE NOTICE 'Deleted % coupons.', v_deleted;
    ELSE
        RAISE NOTICE 'No coupons found matching the criteria.';
    END IF;
END $$;
