-- Post-cutover smoke test — demodb.demo (Aurora PostgreSQL)
-- Run as the application user, NOT as postgres, so it also proves privileges are correct.
--   psql -h <writer-endpoint> -U <app_user> -d demodb -v ON_ERROR_STOP=1 -f smoke-test.sql
-- Every check below RAISES on failure, so a non-zero exit means "do not open to traffic".

\set ON_ERROR_STOP on
SET search_path = demo, public;

-- 1. Object inventory: 14 tables, 16 FKs, 1 trigger, 1 GIN index, 28 routines
DO $$
DECLARE t int; fk int; tg int; gin_ix int; fn int; pr int;
BEGIN
    SELECT count(*) INTO t FROM information_schema.tables
      WHERE table_schema='demo' AND table_type='BASE TABLE';
    SELECT count(*) INTO fk FROM information_schema.table_constraints
      WHERE table_schema='demo' AND constraint_type='FOREIGN KEY';
    SELECT count(*) INTO tg FROM pg_trigger tr
      JOIN pg_class c ON c.oid=tr.tgrelid JOIN pg_namespace n ON n.oid=c.relnamespace
      WHERE n.nspname='demo' AND NOT tr.tgisinternal;
    SELECT count(*) INTO gin_ix FROM pg_index i
      JOIN pg_class c ON c.oid=i.indexrelid JOIN pg_am am ON am.oid=c.relam
      JOIN pg_namespace n ON n.oid=c.relnamespace
      WHERE n.nspname='demo' AND am.amname='gin';
    SELECT count(*) FILTER (WHERE prokind='f'), count(*) FILTER (WHERE prokind='p')
      INTO fn, pr FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace
      WHERE n.nspname='demo';

    IF t <> 14      THEN RAISE EXCEPTION 'tables: expected 14, got %', t;      END IF;
    IF fk <> 16     THEN RAISE EXCEPTION 'foreign keys: expected 16, got %', fk; END IF;
    IF tg <> 1      THEN RAISE EXCEPTION 'triggers: expected 1, got %', tg;     END IF;
    IF gin_ix <> 1  THEN RAISE EXCEPTION 'GIN full-text index missing (got %)', gin_ix; END IF;
    IF fn <> 18     THEN RAISE EXCEPTION 'functions: expected 18, got %', fn;   END IF;
    IF pr <> 10     THEN RAISE EXCEPTION 'procedures: expected 10, got %', pr;  END IF;
    RAISE NOTICE 'objects OK: % tables, % FKs, % trigger, % GIN, % functions, % procedures', t, fk, tg, gin_ix, fn, pr;
END $$;

-- 2. Row counts must equal the source counts captured at freeze time.
--    Replace the expected values if the final sync moved more rows.
DO $$
DECLARE r record; expected jsonb := '{
  "addresses":3, "books":56, "books_cover":56, "book_types":3, "conditions":4,
  "customers":3, "genres":8, "listings":56, "publishers":10,
  "orders":0, "order_items":0, "password_reset_tokens":0,
  "persistent_logins":0, "shopping_cart_items":0 }';
  actual bigint; k text;
BEGIN
    FOR k IN SELECT jsonb_object_keys(expected) LOOP
        EXECUTE format('SELECT count(*) FROM demo.%I', k) INTO actual;
        IF actual <> (expected->>k)::bigint THEN
            RAISE EXCEPTION 'row count %: expected %, got %', k, expected->>k, actual;
        END IF;
    END LOOP;
    RAISE NOTICE 'row counts OK (199 rows across 14 tables)';
END $$;

-- 3. Identity sequences must be ahead of MAX(id) — otherwise the first app insert collides.
DO $$
DECLARE r record; mx bigint; nextv bigint; bad text := '';
BEGIN
    FOR r IN
        SELECT c.relname AS tbl, a.attname AS col, s.relname AS seq
        FROM pg_class c
        JOIN pg_namespace n ON n.oid=c.relnamespace
        JOIN pg_attribute a ON a.attrelid=c.oid AND a.attidentity <> ''
        JOIN pg_depend d ON d.refobjid=c.oid AND d.refobjsubid=a.attnum AND d.classid='pg_class'::regclass
        JOIN pg_class s ON s.oid=d.objid AND s.relkind='S'
        WHERE n.nspname='demo'
    LOOP
        EXECUTE format('SELECT coalesce(max(%I),0) FROM demo.%I', r.col, r.tbl) INTO mx;
        EXECUTE format('SELECT CASE WHEN is_called THEN last_value+1 ELSE last_value END FROM demo.%I', r.seq) INTO nextv;
        IF nextv <= mx THEN bad := bad || format('%s(next=%s,max=%s) ', r.tbl, nextv, mx); END IF;
    END LOOP;
    IF bad <> '' THEN RAISE EXCEPTION 'identity sequence(s) behind MAX(id): %', bad; END IF;
    RAISE NOTICE 'identity sequences OK (all 12 ahead of MAX(id))';
END $$;

-- 4. Full-text search must work AND use the GIN index.
DO $$
DECLARE hits int; plan text := ''; r record;
BEGIN
    SELECT count(*) INTO hits FROM demo.books
      WHERE to_tsvector('english', coalesce(search_text,'')) @@ to_tsquery('english','iron');
    IF hits < 1 THEN RAISE EXCEPTION 'full-text search returned no hits for a known term'; END IF;

    FOR r IN EXECUTE
        'EXPLAIN SELECT id FROM demo.books '
        'WHERE to_tsvector(''english'', coalesce(search_text,'''')) @@ to_tsquery(''english'',''iron'')'
    LOOP
        plan := plan || ' ' || r."QUERY PLAN";
    END LOOP;

    IF plan NOT ILIKE '%books_text_idx%' THEN
        RAISE EXCEPTION 'full-text query is NOT using books_text_idx. Plan:%', plan;
    END IF;
    RAISE NOTICE 'full-text search OK (% hits, using books_text_idx)', hits;
END $$;

-- 5. The search trigger must populate search_text on write.
--    Self-contained: the BEGIN/EXCEPTION block is an implicit subtransaction, so raising the
--    sentinel undoes the INSERT. Leaves no test row behind and needs no outer transaction.
DO $$
DECLARE v text;
BEGIN
    BEGIN
        INSERT INTO demo.books (title, author, isbn) VALUES ('Smoke Test','Ada Lovelace','12345X');
        SELECT search_text INTO v FROM demo.books WHERE title='Smoke Test';
        IF v IS DISTINCT FROM 'smoke test ada lovelace 12345x' THEN
            RAISE EXCEPTION 'BAD_SEARCH_TEXT:%', v;
        END IF;
        RAISE EXCEPTION 'UNDO_SENTINEL';
    EXCEPTION
        WHEN OTHERS THEN
            IF SQLERRM LIKE 'BAD_SEARCH_TEXT:%' THEN
                RAISE EXCEPTION 'search trigger produced unexpected value -> %',
                    replace(SQLERRM,'BAD_SEARCH_TEXT:','');
            ELSIF SQLERRM <> 'UNDO_SENTINEL' THEN
                RAISE;
            END IF;
    END;
    RAISE NOTICE 'search trigger OK (derived: smoke test ada lovelace 12345x, insert rolled back)';
END $$;

-- 6. Representative business routines must answer (values, not just "no error").
DO $$
DECLARE nm text; v numeric;
BEGIN
    SELECT demo.get_genre_name(1)            INTO nm; RAISE NOTICE 'get_genre_name(1) = %', nm;
    SELECT demo.get_condition_name(1)        INTO nm; RAISE NOTICE 'get_condition_name(1) = %', nm;
    SELECT demo.get_customer_full_name(1)    INTO nm; RAISE NOTICE 'get_customer_full_name(1) = %', nm;
    IF nm = 'Unknown Customer' THEN RAISE EXCEPTION 'customer 1 not found — data missing?'; END IF;
    SELECT demo.validation_pkg_is_valid_isbn('978-0-3855-34635') INTO v;
    IF v <> 1 THEN RAISE EXCEPTION 'is_valid_isbn regression (regexp g-flag?): got %', v; END IF;
    SELECT demo.get_customer_lifetime_value(1) INTO v;
    IF v IS NULL THEN RAISE EXCEPTION 'get_customer_lifetime_value returned NULL, expected 0'; END IF;
    RAISE NOTICE 'business routines OK';
END $$;

-- 7. Error contract: the app relies on U0001 / U0002 (NOT P0001/P0002).
DO $$
BEGIN
    BEGIN
        CALL demo.process_customer_offer(999999, 'BOGUS', 1, 'smoke');
        RAISE EXCEPTION 'expected U0002 was not raised';
    EXCEPTION WHEN SQLSTATE 'U0002' THEN
        RAISE NOTICE 'error contract OK: U0002 raised for invalid action';
    END;
END $$;

\echo '*** SMOKE TEST PASSED — safe to open to traffic ***'
