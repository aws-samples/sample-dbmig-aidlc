-- CHOOSE(i, a, b, ...) -> (ARRAY[a, b, ...])[i]  (both NULL when i is out of range).
CREATE OR REPLACE VIEW dbo.vwregionalsales (regionname, regionsalessum) AS
SELECT (ARRAY['North America','Europe','Asia','South America','Africa','Australia','Middle East',
              'Central America','Eastern Europe','Western Europe'])[regionid::int],
       sum(quantity * saleprice)
FROM dbo.productsales
GROUP BY 1;
