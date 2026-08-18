-- Converted from Oracle DEMO.ORDER_PKG (PACKAGE BODY) -> intentionally a NO-OP.
--
-- Rationale: Oracle splits a package into a SPEC (declarations) and a BODY
-- (implementations). PostgreSQL has neither -- each subprogram becomes ONE schema-level
-- routine that carries its own signature and body. The complete conversion of
-- ORDER_PKG (spec + body converted together, holistically) therefore lives in a single file:
--
--     code/demo/package__order_pkg.sql   ->   demo.order_pkg_<subprogram>(...)
--
-- Emitting the routines again here would only re-run identical CREATE OR REPLACE
-- statements. This file is kept so every source object in the inventory keeps a
-- traceable 1:1 artifact in the manifest.
-- Ref: checks/package-naming.md, non-portable-constructs.md -> Packages

DO $$ BEGIN NULL; END $$;
