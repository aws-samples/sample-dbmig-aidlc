-- dbmig target-prep — RECREATE secondary objects AFTER the data load
-- target schema: adventureworks_humanresources   generated: 2026-10-30T09:39:36Z
-- foreign_keys=6 indexes=5 triggers=1  (primary/unique keys are intentionally kept)

-- indexs (5)
CREATE INDEX ix_employee_ix_employee_organizationlevel_organizationnode ON adventureworks_humanresources.employee USING btree (organizationlevel, organizationnode);
CREATE INDEX ix_employee_ix_employee_organizationnode ON adventureworks_humanresources.employee USING btree (organizationnode);
CREATE INDEX "ix_employeedepartmenthistory_ix_employeedepartmenthist$3e917ebd" ON adventureworks_humanresources.employeedepartmenthistory USING btree (shiftid);
CREATE INDEX "ix_employeedepartmenthistory_ix_employeedepartmenthist$6e69a24d" ON adventureworks_humanresources.employeedepartmenthistory USING btree (departmentid);
CREATE INDEX ix_jobcandidate_ix_jobcandidate_businessentityid ON adventureworks_humanresources.jobcandidate USING btree (businessentityid);

-- triggers (1)
CREATE TRIGGER demployee BEFORE DELETE ON adventureworks_humanresources.employee FOR EACH ROW EXECUTE FUNCTION adventureworks_humanresources.fn_demployee();

-- foreign keys (6)
ALTER TABLE "adventureworks_humanresources"."employee" ADD CONSTRAINT "fk_employee_person_businessentityid_939150391" FOREIGN KEY (businessentityid) REFERENCES adventureworks_person.person(businessentityid);
ALTER TABLE "adventureworks_humanresources"."employeedepartmenthistory" ADD CONSTRAINT "fk_employeedepartmenthistory_department_departmentid_955150448" FOREIGN KEY (departmentid) REFERENCES adventureworks_humanresources.department(departmentid);
ALTER TABLE "adventureworks_humanresources"."employeedepartmenthistory" ADD CONSTRAINT "fk_employeedepartmenthistory_employee_businessentityid_97115050" FOREIGN KEY (businessentityid) REFERENCES adventureworks_humanresources.employee(businessentityid);
ALTER TABLE "adventureworks_humanresources"."employeedepartmenthistory" ADD CONSTRAINT "fk_employeedepartmenthistory_shift_shiftid_987150562" FOREIGN KEY (shiftid) REFERENCES adventureworks_humanresources.shift(shiftid);
ALTER TABLE "adventureworks_humanresources"."employeepayhistory" ADD CONSTRAINT "fk_employeepayhistory_employee_businessentityid_1003150619" FOREIGN KEY (businessentityid) REFERENCES adventureworks_humanresources.employee(businessentityid);
ALTER TABLE "adventureworks_humanresources"."jobcandidate" ADD CONSTRAINT "fk_jobcandidate_employee_businessentityid_1019150676" FOREIGN KEY (businessentityid) REFERENCES adventureworks_humanresources.employee(businessentityid);
