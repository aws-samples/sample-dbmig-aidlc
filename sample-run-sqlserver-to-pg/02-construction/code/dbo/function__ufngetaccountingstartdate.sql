CREATE OR REPLACE FUNCTION dbo.ufngetaccountingstartdate()
RETURNS timestamp(3) LANGUAGE sql IMMUTABLE AS $$
    SELECT timestamp '2003-07-01 00:00:00'
$$;
