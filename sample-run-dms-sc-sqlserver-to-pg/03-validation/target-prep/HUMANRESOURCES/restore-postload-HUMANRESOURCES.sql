-- dbmig target-prep — RECREATE secondary objects AFTER the data load
-- target schema: humanresources   generated: 2026-09-02T07:40:27Z
-- foreign_keys=6 indexes=5 triggers=1  (primary/unique keys are intentionally kept)

-- indexs (5)
CREATE INDEX ix_employee_ix_employee_organizationlevel_organizationnode ON humanresources.employee USING btree (organizationlevel, organizationnode);
CREATE INDEX ix_employee_ix_employee_organizationnode ON humanresources.employee USING btree (organizationnode);
CREATE INDEX "ix_employeedepartmenthistory_ix_employeedepartmenthist$3e917ebd" ON humanresources.employeedepartmenthistory USING btree (shiftid);
CREATE INDEX "ix_employeedepartmenthistory_ix_employeedepartmenthist$6e69a24d" ON humanresources.employeedepartmenthistory USING btree (departmentid);
CREATE INDEX ix_jobcandidate_ix_jobcandidate_businessentityid ON humanresources.jobcandidate USING btree (businessentityid);

-- triggers (1)
CREATE TRIGGER tr_employee_biu BEFORE INSERT OR UPDATE ON humanresources.employee FOR EACH ROW EXECUTE FUNCTION humanresources.fn_tr_employee_biu();

-- foreign keys (6)
ALTER TABLE "humanresources"."employee" ADD CONSTRAINT "fk_employee_person_businessentityid_939150391" FOREIGN KEY (businessentityid) REFERENCES person.person(businessentityid);
ALTER TABLE "humanresources"."employeedepartmenthistory" ADD CONSTRAINT "fk_employeedepartmenthistory_department_departmentid_955150448" FOREIGN KEY (departmentid) REFERENCES humanresources.department(departmentid);
ALTER TABLE "humanresources"."employeedepartmenthistory" ADD CONSTRAINT "fk_employeedepartmenthistory_employee_businessentityid_97115050" FOREIGN KEY (businessentityid) REFERENCES humanresources.employee(businessentityid);
ALTER TABLE "humanresources"."employeedepartmenthistory" ADD CONSTRAINT "fk_employeedepartmenthistory_shift_shiftid_987150562" FOREIGN KEY (shiftid) REFERENCES humanresources.shift(shiftid);
ALTER TABLE "humanresources"."employeepayhistory" ADD CONSTRAINT "fk_employeepayhistory_employee_businessentityid_1003150619" FOREIGN KEY (businessentityid) REFERENCES humanresources.employee(businessentityid);
ALTER TABLE "humanresources"."jobcandidate" ADD CONSTRAINT "fk_jobcandidate_employee_businessentityid_1019150676" FOREIGN KEY (businessentityid) REFERENCES humanresources.employee(businessentityid);
