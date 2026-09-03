ALTER TABLE person.person
ADD CONSTRAINT ck_person_persontype_50099219 CHECK (
(persontype IS NULL OR (LOWER(UPPER(persontype)) = LOWER('GC') OR LOWER(UPPER(persontype)) = LOWER('SP') OR LOWER(UPPER(persontype)) = LOWER('EM') OR LOWER(UPPER(persontype)) = LOWER('IN') OR LOWER(UPPER(persontype)) = LOWER('VC') OR LOWER(UPPER(persontype)) = LOWER('SC'))));