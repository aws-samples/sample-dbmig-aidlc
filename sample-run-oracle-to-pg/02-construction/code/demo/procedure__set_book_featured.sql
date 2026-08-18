-- Converted from Oracle DEMO.SET_BOOK_FEATURED -> PostgreSQL demo.set_book_featured
-- Decisions:
--   SYSTIMESTAMP -> now()
--   COMMIT       -> REMOVED (caller owns the transaction)
--   is_featured is smallint on the target (Oracle NUMBER(1,0) 0/1 flag), so the numeric
--   parameter is cast explicitly: PostgreSQL will not implicitly coerce numeric -> smallint
--   in an UPDATE the way Oracle does. Ref: equivalence-spec.md §6 (implicit coercion)

CREATE OR REPLACE PROCEDURE demo.set_book_featured(
    p_book_id     numeric,
    p_is_featured numeric
)
LANGUAGE plpgsql
AS $$
BEGIN
    UPDATE demo.listings
    SET is_featured = p_is_featured::smallint,
        updated_on  = now()
    WHERE book_id = p_book_id
      AND listing_type = 'STORE'
      AND status = 1;
END;
$$;
