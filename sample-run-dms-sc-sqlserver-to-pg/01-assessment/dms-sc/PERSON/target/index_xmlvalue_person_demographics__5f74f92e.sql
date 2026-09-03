CREATE INDEX ix_person_xmlvalue_person_demographics
ON person.person
USING BTREE (demographics ASC);