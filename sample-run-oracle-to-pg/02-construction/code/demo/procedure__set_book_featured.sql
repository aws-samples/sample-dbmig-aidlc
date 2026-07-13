-- DEMO.SET_BOOK_FEATURED -> demo.set_book_featured
CREATE OR REPLACE PROCEDURE demo.set_book_featured(
    p_book_id     bigint,
    p_is_featured numeric)
AS $$
BEGIN
  UPDATE demo.listings
     SET is_featured = p_is_featured, updated_on = now()
   WHERE book_id = p_book_id
     AND listing_type = 'STORE'
     AND status = 1;
END;
$$ LANGUAGE plpgsql;
