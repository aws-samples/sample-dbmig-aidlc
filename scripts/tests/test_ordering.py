from dbmig.engines.base import topological_tiers
from dbmig.conversion.prompt_builder import _format_sample


def test_tiers_parents_before_children():
    names = ["child", "parent", "grandchild"]
    deps = {"child": {"parent"}, "grandchild": {"child"}, "parent": set()}
    flat = [t for tier in topological_tiers(names, deps) for t in tier]
    assert flat.index("parent") < flat.index("child") < flat.index("grandchild")


def test_tiers_cycle_emitted_together():
    tiers = topological_tiers(["a", "b"], {"a": {"b"}, "b": {"a"}})
    assert sorted(t for tier in tiers for t in tier) == ["a", "b"]


def test_tiers_ignores_out_of_scope_and_self():
    assert topological_tiers(["x"], {"x": {"notinscope", "x"}}) == [["x"]]


def test_format_sample_elides_binary():
    s = _format_sample({"t": (["id", "img"], [(1, b"\x00" * 1000)])})
    assert "<binary 1000 bytes>" in s


def test_format_sample_truncates_long_values():
    s = _format_sample({"t": (["c"], [("x" * 500,)])}, max_cell=50)
    assert "…" in s
    assert max(len(line) for line in s.splitlines()) < 120
