CREATE OR REPLACE FUNCTION adventureworks_dbo.ufnleadingzeros(IN par_value INTEGER)
RETURNS VARCHAR
AS
$BODY$
DECLARE
    var_ReturnValue VARCHAR(8);
BEGIN
    var_ReturnValue := CAST (par_Value AS VARCHAR(8));
    var_ReturnValue := REPEAT('0',
    CASE
        WHEN 8 - DATALENGTH(var_ReturnValue) < 0 THEN NULL::INT
        ELSE 8 - DATALENGTH(var_ReturnValue)
    END) || var_ReturnValue;
    RETURN (var_ReturnValue);
END;
$BODY$
LANGUAGE  plpgsql;