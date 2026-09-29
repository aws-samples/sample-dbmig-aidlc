CREATE OR REPLACE FUNCTION demo.get_customer_full_name(p_customer_id numeric)
RETURNS varchar LANGUAGE plpgsql STABLE AS $$
DECLARE
    v_name varchar(500);
BEGIN
    -- Oracle '||' treats NULL as ''; PostgreSQL propagates NULL -> coalesce operands
    SELECT coalesce(first_name, '') || ' ' || coalesce(last_name, '')
    INTO STRICT v_name
    FROM demo.customers WHERE id = p_customer_id;
    RETURN v_name;
EXCEPTION
    WHEN NO_DATA_FOUND THEN
        RETURN 'Unknown Customer';
END $$;
