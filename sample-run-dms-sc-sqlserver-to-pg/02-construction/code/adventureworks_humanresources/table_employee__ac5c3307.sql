-- MANUAL reconversion of HumanResources.Employee (7657 hierarchyid, 7708 GetLevel(), 7679).
-- The table itself was applied by DMS SC and is kept. Only the computed column is fixed.
--
-- Source:  OrganizationLevel AS ([OrganizationNode].[GetLevel]())   -- computed, indexed
-- DMS SC:  organizationlevel smallint (plain column) + BEFORE INSERT/UPDATE trigger
--          tr_employee_biu that only RAISEs when a value is supplied. The GetLevel() body
--          was left as a comment, so the column is ALWAYS NULL on the target (every
--          employee has level NULL instead of 0..4). Row counts still match, so `compare`
--          does not catch it.
-- Here:    organizationnode is varchar holding the hierarchyid string form ('/', '/1/',
--          '/1/2/'), as DMS SC converted it (datatype-map.yaml hierarchyid: "a canonical text path like '/1/2/'"). The
--          level is the number of path steps: count('/') - 1; NULL node -> NULL level.
--          STORED, because the column is indexed (IX_Employee_OrganizationLevel_OrganizationNode)
--          and PG 18 virtual columns cannot be indexed
--          (target-baseline-aurora-postgresql-18.md: computed columns).
-- Note:    ADD COLUMN puts organizationlevel at the end of the column list; nothing in the
--          migrated schema selects Employee with SELECT *.
DROP TRIGGER IF EXISTS tr_employee_biu ON adventureworks_humanresources.employee;
DROP FUNCTION IF EXISTS adventureworks_humanresources.fn_tr_employee_biu();
ALTER TABLE adventureworks_humanresources.employee DROP COLUMN IF EXISTS organizationlevel;
ALTER TABLE adventureworks_humanresources.employee
    ADD COLUMN organizationlevel smallint GENERATED ALWAYS AS (
        (length(organizationnode) - length(replace(organizationnode, '/', '')) - 1)::smallint
    ) STORED;
CREATE INDEX IF NOT EXISTS ix_employee_ix_employee_organizationlevel_organizationnode
    ON adventureworks_humanresources.employee USING btree (organizationlevel, organizationnode);
