from dbmig.conversion.naming import flatten_name, find_flatten_conflicts


def test_flatten_name():
    assert flatten_name("BOOK_PKG", "GET_AVG_PRICE") == "book_pkg_get_avg_price"
    assert flatten_name(None, "GET_GENRE_NAME") == "get_genre_name"
    assert flatten_name("PKG", "FN", separator="$") == "pkg$fn"


def test_clean_no_conflict():
    routines = [
        {"package": "BOOK_PKG", "name": "GET_AVG_PRICE"},
        {"package": "ORDER_PKG", "name": "CREATE_ORDER"},
        {"package": None, "name": "GET_GENRE_NAME"},
    ]
    assert find_flatten_conflicts(routines) == []


def test_cross_object_collision():
    # BOOK_PKG.GET_X and BOOK.PKG_GET_X both -> book_pkg_get_x
    routines = [
        {"package": "BOOK_PKG", "name": "GET_X"},
        {"package": "BOOK", "name": "PKG_GET_X"},
    ]
    conflicts = find_flatten_conflicts(routines)
    assert len(conflicts) == 1
    c = conflicts[0]
    assert c["kind"] == "collision" and c["severity"] == "high"
    assert c["flattened"] == "book_pkg_get_x"
    assert c["involves_standalone"] is False
    assert set(c["sources"]) == {"BOOK_PKG.GET_X", "BOOK.PKG_GET_X"}


def test_shadows_standalone():
    routines = [
        {"package": "AUDIT", "name": "LOG"},
        {"package": None, "name": "AUDIT_LOG"},
    ]
    conflicts = find_flatten_conflicts(routines)
    assert len(conflicts) == 1
    assert conflicts[0]["kind"] == "collision"
    assert conflicts[0]["involves_standalone"] is True


def test_overload_is_medium_not_collision():
    routines = [
        {"package": "P", "name": "F", "overload": "1"},
        {"package": "P", "name": "F", "overload": "2"},
    ]
    conflicts = find_flatten_conflicts(routines)
    assert len(conflicts) == 1
    assert conflicts[0]["kind"] == "overload"
    assert conflicts[0]["severity"] == "medium"
    assert conflicts[0]["overloads"] == 2


def test_dollar_separator_avoids_underscore_collision():
    # The collision under '_' disappears under '$' (AWS SCT style).
    routines = [
        {"package": "BOOK_PKG", "name": "GET_X"},
        {"package": "BOOK", "name": "PKG_GET_X"},
    ]
    assert find_flatten_conflicts(routines, separator="$") == []
