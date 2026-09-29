-- OUT parameters: PostgreSQL 14+ procedure OUT params; call as
--   CALL demo.generate_sales_report(start, end, NULL, NULL, NULL);
CREATE OR REPLACE PROCEDURE demo.generate_sales_report(
    p_start_date timestamp(0), p_end_date timestamp(0),
    OUT p_total_orders numeric, OUT p_total_revenue numeric, OUT p_avg_order_value numeric)
LANGUAGE plpgsql AS $$
BEGIN
    SELECT count(*), coalesce(sum(total_amount), 0), coalesce(avg(total_amount), 0)
    INTO p_total_orders, p_total_revenue, p_avg_order_value
    FROM demo.orders
    WHERE created_on BETWEEN p_start_date AND p_end_date AND status NOT IN ('CANCELLED');
END $$;
