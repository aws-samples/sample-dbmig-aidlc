-- CURSOR VARYING OUTPUT -> set-returning FUNCTION (the app consumes it as a normal query:
-- SELECT * FROM dbo.uspgetproductdata()). A refcursor would have to be fetched inside the same
-- transaction; the result-set form is the recommended conversion (app call-site change).
CREATE OR REPLACE FUNCTION dbo.uspgetproductdata()
RETURNS TABLE (productid integer, name varchar, productnumber varchar, safetystocklevel smallint)
LANGUAGE sql STABLE AS $$
    SELECT productid, name::varchar, productnumber::varchar, safetystocklevel FROM dbo.product
$$;
