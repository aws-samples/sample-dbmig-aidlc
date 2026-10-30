"""DMS SC projects that were converted or exported more than once."""
import json
import os

from dbmig.dmssc.parser import load_apply_results, parse_project


def _node(path, node):
    path.write_text(json.dumps({"content": [node]}))


def test_latest_apply_result_wins(tmp_path):
    ar = tmp_path / "apply-result"
    ar.mkdir()
    (ar / "ar-b.csv").write_text('"Full Path","Timestamp","Status","Error"\n'
                                 '"S.t1","2026-10-30 08:49:40","ERROR","schema missing"\n')
    (ar / "ar-a.csv").write_text('"Full Path","Timestamp","Status","Error"\n'
                                 '"S.t1","2026-10-30 09:10:00","SUCCESS",""\n')
    assert load_apply_results(str(tmp_path))["S.T1"]["status"] == "SUCCESS"


def test_newest_target_node_wins(tmp_path):
    s = tmp_path / "s-SRC"
    t = tmp_path / "t-TGT"
    s.mkdir()
    t.mkdir()
    sid = "Servers.SRC.Databases.DB.Schemas.HR.Tables.Dept"
    _node(s / "Databases.DB.Schemas.HR.Tables.Dept",
          {"meta-type": "TABLE", "id": sid, "name": "Dept",
           "locator": {"schema-name": "HR", "table-name": "Dept"}, "sql": "CREATE TABLE Dept (id int)"})
    old = t / "Schemas.db_hr.Tables.dept"
    new = t / "Schemas.hr.Tables.dept"
    for f, schema in ((old, "db_hr"), (new, "hr")):
        _node(f, {"meta-type": "TABLE", "id": f"Servers.TGT.Schemas.{schema}.Tables.dept", "name": "dept",
                  "locator": {"schema-name": schema, "table-name": "dept"},
                  "synchronization_object": {"name": sid}, "sql": f"CREATE TABLE {schema}.dept (id int)"})
    os.utime(old, (1_000, 1_000))
    os.utime(new, (2_000, 2_000))
    res = parse_project(str(tmp_path))
    (obj,) = [o for o in res.objects if o.source_name == "Dept"]
    assert obj.target_schema == "hr" and "hr.dept" in obj.target_ddl
    assert len(res.superseded_targets) == 1


def test_same_kind_target_beats_generated_helper(tmp_path):
    # DMS SC emits a trigger node for a table (synchronization_object = the table);
    # the TABLE node must be the mapping even when the trigger file is newer.
    s = tmp_path / "s-SRC"
    t = tmp_path / "t-TGT"
    s.mkdir()
    t.mkdir()
    sid = "Servers.SRC.Databases.DB.Schemas.HR.Tables.Employee"
    _node(s / "Databases.DB.Schemas.HR.Tables.Employee",
          {"meta-type": "TABLE", "id": sid, "name": "Employee",
           "locator": {"schema-name": "HR", "table-name": "Employee"}, "sql": "CREATE TABLE Employee (id int)"})
    tab = t / "Schemas.hr.Tables.employee"
    trg = t / "Schemas.hr.Tables.employee.Triggers.tr_employee_biu"
    _node(tab, {"meta-type": "TABLE", "id": "Servers.TGT.Schemas.hr.Tables.employee", "name": "employee",
                "locator": {"schema-name": "hr", "table-name": "employee"},
                "synchronization_object": {"name": sid}, "sql": "CREATE TABLE hr.employee (id int)"})
    _node(trg, {"meta-type": "TRIGGER", "id": "Servers.TGT.Schemas.hr.Tables.employee.Triggers.tr_employee_biu",
                "name": "tr_employee_biu", "locator": {"schema-name": "hr", "table-name": "employee",
                                                        "trigger-name": "tr_employee_biu"},
                "synchronization_object": {"name": sid}, "sql": "CREATE TRIGGER tr_employee_biu ..."})
    os.utime(tab, (1_000, 1_000))
    os.utime(trg, (2_000, 2_000))
    res = parse_project(str(tmp_path))
    (obj,) = [o for o in res.objects if o.source_name == "Employee"]
    assert obj.target_type == "TABLE" and res.superseded_targets == []


def test_live_name_truncation():
    from dbmig.commands.diff_target import _live_name
    long = "fk_businessentityaddress_businessentity_businessentityid_731149650"
    assert len(long) == 66
    assert _live_name(long, "postgresql") == long[:63]
    assert _live_name("short", "postgresql") == "short"
    assert _live_name(long, "oracle") == long


def test_code_units_are_not_split(monkeypatch, tmp_path):
    # A trigger code unit (function + CREATE TRIGGER) must be applied whole by
    # `apply-schema --code`; the deferral split is for table units only.
    import inspect
    from dbmig.commands import apply_schema
    src = inspect.getsource(apply_schema.run)
    assert "if code:" in src and "pre_sql, post_sql = full, \"\"" in src


def test_resolve_target_schema(tmp_path, monkeypatch):
    """--target-schema wins, then the DMS SC map's target_schema, then lower(schema)."""
    import json
    from types import SimpleNamespace
    from dbmig import config
    monkeypatch.setenv("DBMIG_MIGRATIONS_DIR", str(tmp_path))
    a = SimpleNamespace(schema="PERSON", project="p1", target_schema=None)
    assert config.resolve_target_schema(a) == "person"
    d = tmp_path / "p1" / "01-assessment"
    d.mkdir(parents=True)
    (d / "dms-sc-map-PERSON.json").write_text(
        json.dumps({"target_schema": "adventureworks_person"}))
    assert config.resolve_target_schema(a) == "adventureworks_person"
    a.target_schema = "Custom"
    assert config.resolve_target_schema(a) == "custom"


def test_copy_rows_writes_bool_as_int():
    """bit -> numeric(1,0) (DMS SC) must not receive COPY's 't'/'f'."""
    from dbmig.engines import postgresql as pg
    written = []

    class _Copy:
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def write_row(self, r): written.append(list(r))

    class _Cur:
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def copy(self, sql): return _Copy()

    class _Conn:
        def cursor(self): return _Cur()
        def commit(self): pass

    n = pg.copy_rows(_Conn(), "s", "t", ["a", "b", "c"], [(True, 2, "x"), (False, None, "y")])
    assert n == 2
    assert written == [[1, 2, "x"], [0, None, "y"]]
    assert type(written[0][0]) is int


def test_column_action_items_roll_up_to_table(tmp_path):
    """A CRITICAL item on a column node (bare name + parentFullName) marks the table MANUAL."""
    from dbmig.dmssc.classify import classify
    s = tmp_path / "s-SRC"
    s.mkdir()
    sid = "Servers.SRC.Databases.DB.Schemas.HR.Tables.Employee"
    _node(s / "Databases.DB.Schemas.HR.Tables.Employee",
          {"meta-type": "TABLE", "id": sid, "name": "Employee",
           "locator": {"schema-name": "HR", "table-name": "Employee"},
           "sql": "CREATE TABLE Employee (lvl AS (node.GetLevel()))"})
    ai = tmp_path / "action-items"
    (ai / "SRC").mkdir(parents=True)
    (ai / "X-aid").write_text(json.dumps({"7708": {"severityType": "CRITICAL", "topic": "DATATYPES"}}))
    (ai / "SRC" / "Databases.DB.Schemas.HR").write_text(json.dumps({"content": {"treeNodeStatistics": [
        {"type": "table", "name": sid, "statistic": {}, "children": [
            {"type": "column", "name": "OrganizationLevel",
             "statistic": {"parentFullName": sid, "messageActions": [{"code": "7708"}]}}]}]}}))
    res = parse_project(str(tmp_path))
    (obj,) = [o for o in res.objects if o.source_name == "Employee"]
    assert [a.code for a in obj.action_items] == ["7708"]
    assert classify(obj) == "manual"
    assert not res.unmatched_action_items


def test_reimport_keeps_hand_reconverted_code(tmp_path, monkeypatch):
    """Re-running import-dms-sc must not overwrite a MANUAL reconversion."""
    import yaml
    from types import SimpleNamespace
    from dbmig.commands import import_dms_sc
    monkeypatch.setenv("DBMIG_MIGRATIONS_DIR", str(tmp_path / "runs"))
    proj = tmp_path / "proj"
    s = proj / "s-SRC"
    t = proj / "t-TGT"
    s.mkdir(parents=True)
    t.mkdir()
    sid = "Servers.SRC.Databases.DB.Schemas.HR.Procedures.uspFix"
    _node(s / "Databases.DB.Schemas.HR.Procedures.uspFix",
          {"meta-type": "PROCEDURE", "id": sid, "name": "uspFix",
           "locator": {"schema-name": "HR", "procedure-name": "uspFix"}, "sql": "CREATE PROC uspFix AS SELECT 1"})
    _node(t / "Schemas.hr.Procedures.uspfix",
          {"meta-type": "PROCEDURE", "id": "Servers.TGT.Schemas.hr.Procedures.uspfix", "name": "uspfix",
           "locator": {"schema-name": "hr", "procedure-name": "uspfix"},
           "synchronization_object": {"name": sid},
           "sql": "CREATE PROCEDURE hr.uspfix() AS $$\r\nBEGIN /* [7644 - Severity CRITICAL - x] */ END $$"})
    args = SimpleNamespace(dms_sc_dir=str(proj), project="p", schema=None)
    (proj / "action-items").mkdir()
    (proj / "action-items" / "X-ot").write_text(
        json.dumps([{"PROCEDURE": {"objectTypeProperty": "CODE_OBJECT"}}]))
    assert import_dms_sc.run(args) == 0
    constr = tmp_path / "runs" / "p" / "02-construction"
    mpath = constr / "code-manifest-HR.yaml"
    assert import_dms_sc.run(args) == 0          # untouched CRLF output: not "edited"
    m = yaml.safe_load(mpath.read_text())
    (u,) = m["units"]
    assert "reconverted" not in u
    out = constr / u["output_file"]
    out.write_text("-- hand reconversion\n")
    u["status"] = "applied"
    mpath.write_text(yaml.safe_dump(m))

    assert import_dms_sc.run(args) == 0
    (u2,) = yaml.safe_load(mpath.read_text())["units"]
    assert out.read_text() == "-- hand reconversion\n"
    assert u2["status"] == "applied" and u2["reconverted"] is True
