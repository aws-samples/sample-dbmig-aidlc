CREATE INDEX ix_person_xmlproperty_person_demographics
ON adventureworks_person.person
USING BTREE (demographics ASC);