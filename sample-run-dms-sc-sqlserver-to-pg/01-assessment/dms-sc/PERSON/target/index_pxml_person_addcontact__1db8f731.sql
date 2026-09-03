CREATE INDEX ix_person_pxml_person_addcontact
ON person.person
USING BTREE (additionalcontactinfo ASC);