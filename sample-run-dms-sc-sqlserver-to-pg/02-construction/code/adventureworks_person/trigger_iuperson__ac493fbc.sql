CREATE TRIGGER iuperson_after_update
AFTER UPDATE
ON adventureworks_person.person
REFERENCING OLD TABLE AS deleted$dd8b1d18 NEW TABLE AS inserted$dd8b1d18
FOR EACH STATEMENT EXECUTE PROCEDURE adventureworks_person.fn_iuperson();