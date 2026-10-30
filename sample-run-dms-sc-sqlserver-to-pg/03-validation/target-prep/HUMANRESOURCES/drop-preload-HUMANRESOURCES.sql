-- dbmig target-prep — DROP secondary objects BEFORE the data load
-- target schema: adventureworks_humanresources   generated: 2026-10-30T09:39:36Z
-- foreign_keys=6 indexes=5 triggers=1  (primary/unique keys are intentionally kept)

-- foreign keys (6)
ALTER TABLE "adventureworks_humanresources"."employee" DROP CONSTRAINT IF EXISTS "fk_employee_person_businessentityid_939150391";
ALTER TABLE "adventureworks_humanresources"."employeedepartmenthistory" DROP CONSTRAINT IF EXISTS "fk_employeedepartmenthistory_department_departmentid_955150448";
ALTER TABLE "adventureworks_humanresources"."employeedepartmenthistory" DROP CONSTRAINT IF EXISTS "fk_employeedepartmenthistory_employee_businessentityid_97115050";
ALTER TABLE "adventureworks_humanresources"."employeedepartmenthistory" DROP CONSTRAINT IF EXISTS "fk_employeedepartmenthistory_shift_shiftid_987150562";
ALTER TABLE "adventureworks_humanresources"."employeepayhistory" DROP CONSTRAINT IF EXISTS "fk_employeepayhistory_employee_businessentityid_1003150619";
ALTER TABLE "adventureworks_humanresources"."jobcandidate" DROP CONSTRAINT IF EXISTS "fk_jobcandidate_employee_businessentityid_1019150676";

-- triggers (1)
DROP TRIGGER IF EXISTS "demployee" ON "adventureworks_humanresources"."employee";

-- indexs (5)
DROP INDEX IF EXISTS "adventureworks_humanresources"."ix_employee_ix_employee_organizationlevel_organizationnode";
DROP INDEX IF EXISTS "adventureworks_humanresources"."ix_employee_ix_employee_organizationnode";
DROP INDEX IF EXISTS "adventureworks_humanresources"."ix_employeedepartmenthistory_ix_employeedepartmenthist$3e917ebd";
DROP INDEX IF EXISTS "adventureworks_humanresources"."ix_employeedepartmenthistory_ix_employeedepartmenthist$6e69a24d";
DROP INDEX IF EXISTS "adventureworks_humanresources"."ix_jobcandidate_ix_jobcandidate_businessentityid";
