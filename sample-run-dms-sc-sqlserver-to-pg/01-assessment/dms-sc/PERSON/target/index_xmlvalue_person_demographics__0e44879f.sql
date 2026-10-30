CREATE INDEX ix_person_xmlvalue_person_demographics
ON adventureworks_person.person
USING BTREE (demographics ASC);