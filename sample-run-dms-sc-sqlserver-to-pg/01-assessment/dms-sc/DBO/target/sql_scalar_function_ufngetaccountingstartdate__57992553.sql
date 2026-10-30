CREATE OR REPLACE FUNCTION adventureworks_dbo.ufngetaccountingstartdate()
RETURNS TIMESTAMP WITHOUT TIME ZONE
AS
$BODY$
BEGIN
    RETURN aws_sqlserver_ext.conv_string_to_datetime('DATETIME', '20030701', 112);
END;
$BODY$
LANGUAGE  plpgsql;