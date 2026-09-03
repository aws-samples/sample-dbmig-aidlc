ALTER TABLE humanresources.employeepayhistory
ADD CONSTRAINT ck_employeepayhistory_payfrequency_1861581670 CHECK (
(payfrequency = (2) OR payfrequency = (1)));