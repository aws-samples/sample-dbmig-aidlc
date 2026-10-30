-- Package REPORTING_PKG (spec + body) flattened to <package>_<subprogram>.
-- PIPELINED book_sales_tab -> RETURNS TABLE + RETURN QUERY (sql-plsql/user-defined-functions.md).
-- Declared column types match the query's ACTUAL types (b.id bigint, b.title varchar,
-- SUM(bigint) numeric, SUM(numeric) numeric); a mismatch would only fail at execution.
-- FETCH FIRST n ROWS ONLY -> LIMIT. NOTE: ORDER BY total_sold DESC has no tie-breaker in the
-- source, so tied rows may come back in a different order on each engine (compare as a set).
CREATE OR REPLACE FUNCTION demo.reporting_pkg_get_top_books(p_limit numeric DEFAULT 10)
RETURNS TABLE (book_id bigint, title varchar, total_sold numeric, revenue numeric)
LANGUAGE plpgsql STABLE AS $$
BEGIN
    RETURN QUERY
    SELECT b.id, b.title::varchar,
           sum(oi.quantity)::numeric AS total_sold,
           sum(oi.book_price * oi.quantity)::numeric AS revenue
    FROM demo.books b
    JOIN demo.order_items oi ON b.id = oi.book_id
    JOIN demo.orders o ON oi.order_id = o.id
    WHERE o.status NOT IN ('CANCELLED')
    GROUP BY b.id, b.title
    ORDER BY total_sold DESC
    LIMIT p_limit;
END $$;

-- OUT params; TRUNC(created_on) -> date_trunc('day', ...) returned as timestamp(0) (Oracle DATE).
CREATE OR REPLACE PROCEDURE demo.reporting_pkg_get_customer_stats(
    p_customer_id numeric,
    OUT p_total_orders numeric,
    OUT p_total_spent numeric,
    OUT p_avg_order numeric,
    OUT p_last_order_date timestamp(0))
LANGUAGE plpgsql AS $$
BEGIN
    SELECT count(*), coalesce(sum(total_amount), 0), coalesce(avg(total_amount), 0),
           max(date_trunc('day', created_on))
    INTO p_total_orders, p_total_spent, p_avg_order, p_last_order_date
    FROM demo.orders
    WHERE customer_id = p_customer_id AND status NOT IN ('CANCELLED');
END $$;
