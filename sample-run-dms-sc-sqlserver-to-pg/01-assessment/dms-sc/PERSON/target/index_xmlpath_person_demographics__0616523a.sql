CREATE INDEX ix_person_xmlpath_person_demographics
ON adventureworks_person.person
USING BTREE (demographics ASC);