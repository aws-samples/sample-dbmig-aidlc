-- DEMO.GENERATE_SALES_REPORT -> demo.generate_sales_report
-- Oracle OUT params -> PG procedure OUT params. DATE params -> timestamp. NVL -> COALESCE.
CREATE OR REPLACE PROCEDURE demo.generate_sales_report(
    p_start_date       timestamp,
    p_end_date         timestamp,
    OUT p_total_orders    numeric,
    OUT p_total_revenue   numeric,
    OUT p_avg_order_value numeric)
AS $$
BEGIN
  SELECT COUNT(*),
         COALESCE(SUM(total_amount), 0),
         COALESCE(AVG(total_amount), 0)
    INTO p_total_orders, p_total_revenue, p_avg_order_value
  FROM demo.orders
  WHERE created_on BETWEEN p_start_date AND p_end_date
    AND status NOT IN ('CANCELLED');
END;
$$ LANGUAGE plpgsql;
