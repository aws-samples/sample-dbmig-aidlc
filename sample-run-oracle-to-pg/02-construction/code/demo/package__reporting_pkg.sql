-- Converted from Oracle DEMO.REPORTING_PKG (spec + body) -> PostgreSQL demo.reporting_pkg_*
-- Package flattening -> <package>_<subprogram>. Ref: checks/package-naming.md
--
-- Decisions:
--   *** PIPELINED table function redesign ***
--   Oracle: TYPE book_sales_rec IS RECORD / TYPE book_sales_tab IS TABLE OF ... and
--           FUNCTION get_top_books(...) RETURN book_sales_tab PIPELINED with PIPE ROW.
--   PostgreSQL has no PIPELINED functions and needs no companion RECORD/TABLE types:
--           -> a set-returning function RETURNS TABLE(...) with a single RETURN QUERY.
--           The explicit row-by-row FOR ... LOOP + PIPE ROW is collapsed into the query
--           itself, which is both equivalent and faster.
--           Ref: non-portable-constructs.md → PIPELINED table functions
--   FETCH FIRST p_limit ROWS ONLY -> LIMIT p_limit
--   Column types match the converted tables: books.id -> bigint, books.title -> varchar(255).
--   get_customer_stats:
--       NVL -> COALESCE
--       MAX(TRUNC(created_on)) -> max(created_on::date)   (TRUNC(date) -> ::date)
--       OUT p_last_order_date is Oracle DATE-truncated-to-day -> PostgreSQL `date`.
--   Both routines are read-only -> STABLE / no COMMIT to remove.

CREATE OR REPLACE FUNCTION demo.reporting_pkg_get_top_books(p_limit numeric DEFAULT 10)
RETURNS TABLE (
    book_id    bigint,
    title      varchar(255),
    total_sold numeric,
    revenue    numeric
)
LANGUAGE plpgsql
STABLE
AS $$
BEGIN
    RETURN QUERY
    SELECT b.id,
           b.title,
           sum(oi.quantity)                    AS total_sold,
           sum(oi.book_price * oi.quantity)    AS revenue
    FROM demo.books b
    JOIN demo.order_items oi ON b.id = oi.book_id
    JOIN demo.orders o      ON oi.order_id = o.id
    WHERE o.status NOT IN ('CANCELLED')
    GROUP BY b.id, b.title
    ORDER BY total_sold DESC
    LIMIT p_limit;
END;
$$;

CREATE OR REPLACE PROCEDURE demo.reporting_pkg_get_customer_stats(
    p_customer_id         numeric,
    OUT p_total_orders    numeric,
    OUT p_total_spent     numeric,
    OUT p_avg_order       numeric,
    OUT p_last_order_date date
)
LANGUAGE plpgsql
AS $$
BEGIN
    SELECT count(*),
           coalesce(sum(total_amount), 0),
           coalesce(avg(total_amount), 0),
           max(created_on::date)
    INTO p_total_orders, p_total_spent, p_avg_order, p_last_order_date
    FROM demo.orders
    WHERE customer_id = p_customer_id
      AND status NOT IN ('CANCELLED');
END;
$$;
