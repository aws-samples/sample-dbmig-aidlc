CREATE OR REPLACE FUNCTION adventureworks_dbo.ufngetaccountingenddate()
RETURNS TIMESTAMP WITHOUT TIME ZONE
AS
$BODY$
BEGIN
    RETURN (aws_sqlserver_ext.conv_string_to_datetime('DATETIME', '20040701', 112))::TIMESTAMP + (- 2::NUMERIC || ' MILLISECOND')::INTERVAL;
END;
$BODY$
LANGUAGE  plpgsql;