ALTER TABLE person.personphone
ADD CONSTRAINT fk_personphone_phonenumbertype_phonenumbertypeid_1115151018 FOREIGN KEY (phonenumbertypeid) 
REFERENCES person.phonenumbertype (phonenumbertypeid)
ON UPDATE NO ACTION
ON DELETE NO ACTION;