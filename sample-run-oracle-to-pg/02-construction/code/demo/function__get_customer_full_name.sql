-- DEMO.GET_CUSTOMER_FULL_NAME. Oracle || treats NULL as '' ('' = NULL), PostgreSQL || returns NULL:
-- coalesce each operand so a customer with a NULL name part gives the same string.
CREATE OR REPLACE FUNCTION demo.get_customer_full_name(p_customer_id numeric)
RETURNS varchar LANGUAGE plpgsql STABLE AS $$
DECLARE
    v_name varchar(500);
BEGIN
    SELECT coalesce(first_name, '') || ' ' || coalesce(last_name, '')
    INTO STRICT v_name
    FROM demo.customers
    WHERE id = p_customer_id;
    RETURN v_name;
EXCEPTION
    WHEN NO_DATA_FOUND THEN
        RETURN 'Unknown Customer';
END $$;
