"""M2: net-effect (delta) comparison in ``run-tests``.

Numeric probes compare the signed delta; non-numeric probes compare the
*transition* (whether the probed value changed, and its resulting value) WITHOUT
requiring the pre-call snapshots to match across engines — so differing
auto-increment seeds / timestamps no longer cause spurious FAILs, and matching
absolute before/after values no longer cause false PASSes.
"""
from dbmig.commands.run_tests import _delta, _delta_equal

TOL = 1e-9


def test_numeric_delta_is_signed_difference():
    assert _delta(2, 5) == 3.0
    assert _delta(10, 4) == -6.0
    assert _delta_equal(3.0, 3.0, TOL)
    assert not _delta_equal(3.0, 2.0, TOL)


def test_numeric_delta_matches_despite_different_absolute_values():
    # source rows went 100 -> 103 (+3); target went 5 -> 8 (+3). Same net effect.
    assert _delta_equal(_delta(100, 103), _delta(5, 8), TOL)


def test_non_numeric_transition_descriptor():
    assert _delta("PENDING", "CLOSED") == (True, "CLOSED")
    assert _delta("SAME", "SAME") == (False, "SAME")


def test_non_numeric_same_result_different_seed_passes():
    # Different pre-call values (seeds) but both transition to 'CLOSED' -> match.
    sd = _delta("A-before", "CLOSED")
    td = _delta("Z-before", "CLOSED")
    assert _delta_equal(sd, td, TOL)


def test_non_numeric_different_result_fails():
    sd = _delta("x", "CLOSED")
    td = _delta("x", "OPEN")
    assert not _delta_equal(sd, td, TOL)


def test_non_numeric_changedness_must_agree():
    # source changed, target did not -> not equivalent.
    assert not _delta_equal(_delta("a", "b"), _delta("c", "c"), TOL)


def test_non_numeric_both_unchanged_matches():
    assert _delta_equal(_delta("v", "v"), _delta("w", "w"), TOL)


def test_numeric_vs_transition_never_equal():
    assert not _delta_equal(3.0, (True, "x"), TOL)
    assert not _delta_equal((False, "x"), 0.0, TOL)
