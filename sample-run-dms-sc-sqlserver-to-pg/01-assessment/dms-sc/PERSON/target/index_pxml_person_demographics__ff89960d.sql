CREATE INDEX ix_person_pxml_person_demographics
ON person.person
USING BTREE (demographics ASC);