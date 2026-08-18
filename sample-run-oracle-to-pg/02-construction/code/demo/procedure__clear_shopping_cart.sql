-- Converted from Oracle DEMO.CLEAR_SHOPPING_CART -> PostgreSQL demo.clear_shopping_cart
-- Decisions:
--   COMMIT -> REMOVED (caller owns the transaction; required for rolled-back equivalence tests).
--   is_wishlist_item stayed smallint 0/1, so the `= 0` predicate is unchanged.

CREATE OR REPLACE PROCEDURE demo.clear_shopping_cart(p_customer_id numeric)
LANGUAGE plpgsql
AS $$
BEGIN
    DELETE FROM demo.shopping_cart_items
    WHERE customer_id = p_customer_id
      AND is_wishlist_item = 0;
END;
$$;
