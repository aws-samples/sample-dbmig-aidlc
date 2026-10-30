-- DEMO.SET_BOOK_FEATURED. COMMIT removed (caller owns the transaction).
CREATE OR REPLACE PROCEDURE demo.set_book_featured(p_book_id numeric, p_is_featured numeric)
LANGUAGE plpgsql AS $$
BEGIN
    UPDATE demo.listings
    SET is_featured = p_is_featured, updated_on = localtimestamp
    WHERE book_id = p_book_id
      AND listing_type = 'STORE'
      AND status = 1;
END $$;
