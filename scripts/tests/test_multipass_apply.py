from dbmig.engines import _common


def test_multipass_resolves_fk_ordering():
    """CHILD references PARENT; CHILD fails until PARENT exists, then succeeds."""
    created = set()

    def apply_sql(_conn, sql):
        if sql.startswith("CHILD") and "PARENT" not in created:
            return False, "FK: PARENT missing"
        created.add(sql.split()[0])
        return True, None

    files = [("child", "CHILD refs PARENT"), ("parent", "PARENT")]
    results = _common.multipass_apply(apply_sql, None, files)
    by = {r["label"]: r["status"] for r in results}
    assert by == {"child": "applied", "parent": "applied"}


def test_multipass_marks_persistent_failure():
    def apply_sql(_conn, sql):
        return (False, "boom") if "BAD" in sql else (True, None)

    results = _common.multipass_apply(apply_sql, None,
                                      [("ok", "GOOD"), ("bad", "BAD")])
    by = {r["label"]: r["status"] for r in results}
    assert by["ok"] == "applied" and by["bad"] == "failed"


def test_multipass_preserves_input_order():
    results = _common.multipass_apply(lambda c, s: (True, None), None,
                                      [("a", "A"), ("b", "B"), ("c", "C")])
    assert [r["label"] for r in results] == ["a", "b", "c"]
