CREATE INDEX ix_person_xmlproperty_person_demographics
ON person.person
USING BTREE (demographics ASC);