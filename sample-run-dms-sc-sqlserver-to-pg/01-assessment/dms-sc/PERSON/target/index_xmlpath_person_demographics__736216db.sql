CREATE INDEX ix_person_xmlpath_person_demographics
ON person.person
USING BTREE (demographics ASC);