CREATE INDEX ix_personphone_ix_personphone_phonenumber
ON person.personphone
USING BTREE (phonenumber ASC);