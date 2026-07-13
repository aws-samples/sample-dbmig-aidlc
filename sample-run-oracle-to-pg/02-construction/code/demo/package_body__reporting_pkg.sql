-- DEMO.REPORTING_PKG (package body) -> flattened routines demo.reporting_pkg_*
-- PIPELINED table function -> set-returning function (RETURNS TABLE + RETURN QUERY).
-- FETCH FIRST n ROWS ONLY -> LIMIT; TRUNC(created_on) -> created_on::date; NVL -> COALESCE.

CREATE OR REPLACE FUNCTION demo.reporting_pkg_get_top_books(p_limit numeric DEFAULT 10)
RETURNS TABLE(book_id bigint, title varchar, total_sold numeric, revenue numeric)
AS $$
BEGIN
  RETURN QUERY
    SELECT b.id, b.title,
           SUM(oi.quantity)::numeric AS total_sold,
           SUM(oi.book_price * oi.quantity)::numeric AS revenue
    FROM demo.books b
    JOIN demo.order_items oi ON b.id = oi.book_id
    JOIN demo.orders o ON oi.order_id = o.id
    WHERE o.status NOT IN ('CANCELLED')
    GROUP BY b.id, b.title
    ORDER BY total_sold DESC
    LIMIT p_limit;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE PROCEDURE demo.reporting_pkg_get_customer_stats(
    p_customer_id       bigint,
    OUT p_total_orders     numeric,
    OUT p_total_spent      numeric,
    OUT p_avg_order        numeric,
    OUT p_last_order_date  date)
AS $$
BEGIN
  SELECT COUNT(*),
         COALESCE(SUM(total_amount), 0),
         COALESCE(AVG(total_amount), 0),
         MAX(created_on::date)
    INTO p_total_orders, p_total_spent, p_avg_order, p_last_order_date
  FROM demo.orders
  WHERE customer_id = p_customer_id
    AND status NOT IN ('CANCELLED');
END;
$$ LANGUAGE plpgsql;
