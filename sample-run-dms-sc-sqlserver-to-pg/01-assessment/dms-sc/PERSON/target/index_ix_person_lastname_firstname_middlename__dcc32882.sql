CREATE INDEX ix_person_ix_person_lastname_firstname_middlename
ON person.person
USING BTREE (lastname ASC, firstname ASC, middlename ASC);