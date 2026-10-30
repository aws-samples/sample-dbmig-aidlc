CREATE INDEX ix_person_pxml_person_addcontact
ON adventureworks_person.person
USING BTREE (additionalcontactinfo ASC);