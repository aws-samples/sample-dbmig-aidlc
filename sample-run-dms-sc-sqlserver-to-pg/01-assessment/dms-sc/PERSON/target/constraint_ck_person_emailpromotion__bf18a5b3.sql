ALTER TABLE person.person
ADD CONSTRAINT ck_person_emailpromotion_34099162 CHECK (
(emailpromotion >= (0) AND emailpromotion <= (2)));