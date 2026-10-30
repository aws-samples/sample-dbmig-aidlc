ALTER TABLE adventureworks_person.personphone
ADD CONSTRAINT fk_personphone_phonenumbertype_phonenumbertypeid_1115151018 FOREIGN KEY (phonenumbertypeid) 
REFERENCES adventureworks_person.phonenumbertype (phonenumbertypeid)
ON UPDATE NO ACTION
ON DELETE NO ACTION;