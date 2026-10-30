-- DEMO.CLEAR_SHOPPING_CART. COMMIT removed (caller owns the transaction).
CREATE OR REPLACE PROCEDURE demo.clear_shopping_cart(p_customer_id numeric)
LANGUAGE plpgsql AS $$
BEGIN
    DELETE FROM demo.shopping_cart_items
    WHERE customer_id = p_customer_id
      AND is_wishlist_item = 0;
END $$;
