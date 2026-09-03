ALTER TABLE humanresources.employeepayhistory
ADD CONSTRAINT ck_employeepayhistory_rate_1877581727 CHECK (
(rate >= (6.50) AND rate <= (200.00)));