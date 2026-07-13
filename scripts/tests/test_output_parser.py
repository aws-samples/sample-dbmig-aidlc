from dbmig.conversion import output_parser as op


def test_parse_sql_fence():
    txt = "Here:\n```sql\nCREATE TABLE foo(id int);\n```\nDone."
    assert op.parse_ddl(txt).strip() == "CREATE TABLE foo(id int);"


def test_parse_mysql_fence():
    txt = "```mysql\nCREATE TABLE `foo`(id int);\n```"
    assert "CREATE TABLE `foo`(id int);" in op.parse_ddl(txt)


def test_parse_tsql_and_plain():
    assert "CREATE PROC x" in op.parse_ddl("```tsql\nCREATE PROC x\n```")
    assert op.parse_ddl("CREATE TABLE t(x int);").strip() == "CREATE TABLE t(x int);"


def test_multiple_fences_concatenated():
    txt = "```sql\nA;\n```\nmid\n```sql\nB;\n```"
    out = op.parse_ddl(txt)
    assert "A;" in out and "B;" in out


def test_looks_like_sql():
    assert op.looks_like_sql("CREATE TABLE t(x int);")
    assert not op.looks_like_sql("   ")


# ---- M1: non-SQL fences must not leak into executable DDL ----------------

def test_text_fence_dropped_when_sql_present():
    txt = ("Explanation:\n```text\nThis converts the trigger.\n```\n"
           "```sql\nCREATE TABLE t(x int);\n```")
    out = op.parse_ddl(txt)
    assert "CREATE TABLE t(x int);" in out
    assert "This converts the trigger." not in out


def test_json_fence_dropped_when_sql_present():
    txt = '```json\n{"note": "meta"}\n```\n```sql\nCREATE TABLE t(x int);\n```'
    out = op.parse_ddl(txt)
    assert "CREATE TABLE t(x int);" in out
    assert "meta" not in out


def test_empty_tag_fence_kept_when_sql_like():
    txt = "```\nCREATE TABLE t(x int);\n```"
    assert "CREATE TABLE t(x int);" in op.parse_ddl(txt)


def test_plpgsql_fence_kept():
    txt = "```plpgsql\nCREATE FUNCTION f() RETURNS int AS $$ BEGIN RETURN 1; END; $$;\n```"
    assert "CREATE FUNCTION f()" in op.parse_ddl(txt)


def test_only_prose_fence_falls_back_not_empty():
    # If no fenced block qualifies as SQL, fall back to the bodies rather than
    # silently returning nothing (the apply step will surface a real error).
    txt = "```text\nno sql here\n```"
    assert op.parse_ddl(txt).strip() == "no sql here"
