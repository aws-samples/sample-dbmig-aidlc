-- DEMO.GET_CUSTOMER_FULL_NAME -> demo.get_customer_full_name
CREATE OR REPLACE FUNCTION demo.get_customer_full_name(p_customer_id bigint)
RETURNS varchar
AS $$
DECLARE
  v_name varchar(500);
BEGIN
  SELECT first_name || ' ' || last_name INTO STRICT v_name
  FROM demo.customers WHERE id = p_customer_id;
  RETURN v_name;
EXCEPTION
  WHEN NO_DATA_FOUND THEN
    RETURN 'Unknown Customer';
END;
$$ LANGUAGE plpgsql;
