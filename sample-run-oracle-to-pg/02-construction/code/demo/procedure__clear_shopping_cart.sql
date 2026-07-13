-- DEMO.CLEAR_SHOPPING_CART -> demo.clear_shopping_cart
CREATE OR REPLACE PROCEDURE demo.clear_shopping_cart(p_customer_id bigint)
AS $$
BEGIN
  DELETE FROM demo.shopping_cart_items
   WHERE customer_id = p_customer_id
     AND is_wishlist_item = 0;
  -- COMMIT dropped: caller controls the transaction (keeps the equivalence harness's rollback safe).
END;
$$ LANGUAGE plpgsql;
