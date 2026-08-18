-- Converted from Oracle DEMO.GENERATE_SALES_REPORT -> PostgreSQL demo.generate_sales_report
-- Decisions:
--   Oracle DATE parameters -> timestamp(0) (Oracle DATE carries a time component;
--       mapping to `date` would silently truncate the caller's bind values).
--   NVL -> COALESCE.
--   OUT parameters are supported on PostgreSQL procedures (PG 14+); target is 17.7.
--       Callers use: CALL demo.generate_sales_report(:start, :end, NULL, NULL, NULL);
--   Read-only: no COMMIT existed in the source, nothing to remove.

CREATE OR REPLACE PROCEDURE demo.generate_sales_report(
    p_start_date          timestamp(0),
    p_end_date            timestamp(0),
    OUT p_total_orders    numeric,
    OUT p_total_revenue   numeric,
    OUT p_avg_order_value numeric
)
LANGUAGE plpgsql
AS $$
BEGIN
    SELECT count(*),
           coalesce(sum(total_amount), 0),
           coalesce(avg(total_amount), 0)
    INTO p_total_orders, p_total_revenue, p_avg_order_value
    FROM demo.orders
    WHERE created_on BETWEEN p_start_date AND p_end_date
      AND status NOT IN ('CANCELLED');
END;
$$;
