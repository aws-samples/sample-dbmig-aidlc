"""Tests for ``dbmig migrate-data`` planning, resume/durability, column alignment,
virtual-column exclusion, and statistics-driven chunk/shard sizing.

Covers the highest-risk data-mover behaviours:
  * H1 — resume is gated on a chunk-boundary signature, so ordinal skipping only
    happens when boundaries are provably identical; a mismatch (source mutated or
    --batch-size changed) triggers a clean truncate+reload instead of silent
    drop/duplication.
  * H2 — resume state is written atomically (temp file + os.replace) and leaves no
    stray temp files.
  * H3 — a source column missing from the converted target table fails the copy
    loudly and early, before any rows are streamed.
  * VIRTUAL — Oracle VIRTUAL / SQL Server computed columns are converted to target
    GENERATED columns, which reject writes; they must be excluded from data movement
    (``data_columns``) so the copy does not fail on the whole table.
  * STATS — chunk step and shard count are sized by the source row estimate, not by
    the raw PK span, so a sparse PK range does not explode into empty chunks/shards.
"""
import pytest

from dbmig.commands import migrate_data as md
from dbmig.engines.base import SourceEngine


# ---- pure helpers --------------------------------------------------------

def test_chunk_signature_stable_and_boundary_sensitive():
    a = [("SELECT * FROM t WHERE id >= 0 AND id < 10", {}),
         ("SELECT * FROM t WHERE id >= 10 AND id < 20", {})]
    a2 = list(a)  # identical boundaries -> identical signature
    b = [("SELECT * FROM t WHERE id >= 0 AND id < 5", {})]  # different batch size
    assert md._chunk_signature(a) == md._chunk_signature(a2)
    assert md._chunk_signature(a) != md._chunk_signature(b)


def test_chunk_signature_uses_params():
    a = [("SELECT ...", {"lo": 0, "hi": 10})]
    b = [("SELECT ...", {"lo": 0, "hi": 20})]
    assert md._chunk_signature(a) != md._chunk_signature(b)


def test_save_state_is_atomic_and_leaves_no_temp(tmp_path):
    p = tmp_path / "T.json"
    md._save_state(p, {"signature": "s", "done_chunks": 2, "copied": 5,
                       "complete": False})
    assert md._load_state(p) == {"signature": "s", "done_chunks": 2, "copied": 5,
                                 "complete": False}
    # no leftover *.tmp.* files from the atomic-rename write
    assert not list(tmp_path.glob("*.tmp*"))


def test_load_state_tolerates_truncated_json(tmp_path):
    p = tmp_path / "T.json"
    p.write_text('{"signature": "s", "done_chunks": 2,')  # truncated (crash mid-write)
    assert md._load_state(p) == {}


def test_wm_path_includes_shard_suffix(tmp_path, monkeypatch):
    monkeypatch.setattr(md.config, "workspace_dir", lambda project: tmp_path)
    whole = md._wm_path("proj", "APP", "T", None)
    shard = md._wm_path("proj", "APP", "T", 3)
    assert whole.name == "APP.T.json"
    assert shard.name == "APP.T.s003.json"
    assert whole != shard  # a whole-table unit and a shard never share resume state


# ---- STATS: shard count is capped by the source row estimate -------------

def test_effective_shards_caps_by_estimate():
    # 100k rows over a wide range -> at most 100k/50k = 2 shards (not 16 empty ones)
    assert md._effective_shards(16, 100_000) == 2
    # below the per-shard floor -> collapse to a single unit
    assert md._effective_shards(16, 40_000) == 1
    # unknown estimate leaves the request untouched (span-only, legacy behaviour)
    assert md._effective_shards(16, -1) == 16
    # a single-shard request is always honoured
    assert md._effective_shards(1, 10_000_000) == 1
    # a dense/large table keeps the full requested fan-out
    assert md._effective_shards(8, 10_000_000) == 8


def test_shard_ranges_are_disjoint_and_cover():
    ranges = md._shard_ranges(0, 99, 4)
    assert ranges[0][0] == 0 and ranges[-1][1] == 100
    for (_, b), (a2, _) in zip(ranges, ranges[1:]):
        assert b == a2  # half-open, contiguous, no overlap/gap


# ---- fakes for planning + copy -------------------------------------------

class FakeSource:
    """Minimal source used by _plan_units / _copy_unit. ``data_columns`` already
    reflects virtual-column exclusion (the real engines do this via the base
    ``data_columns`` helper, exercised separately below)."""

    def __init__(self, data_cols, pk, chunks=None, rows_by_sql=None,
                 bounds=None, estimate=-1):
        self._data_cols = data_cols
        self._pk = pk
        self._chunks = chunks or []
        self._rows = rows_by_sql or {}
        self._bounds = bounds
        self._estimate = estimate
        self.closed = False

    def data_columns(self, s, t):
        return self._data_cols

    def table_columns(self, s, t):  # not used once data_columns exists, kept for parity
        return self._data_cols

    def primary_key_columns(self, s, t):
        return self._pk

    def numeric_pk_bounds(self, s, t, pk):
        return self._bounds

    def row_estimate(self, s, t):
        return self._estimate

    def chunk_iterator(self, s, t, pk, bs, pk_lo=None, pk_hi=None):
        return iter(self._chunks)

    def fetch_iter(self, sql, params):
        return iter(self._rows.get(sql, []))

    def close(self):
        self.closed = True


class FakeTarget:
    def __init__(self, tcols):
        self._tcols = tcols
        self.inserts = []       # list of (cols, rows)
        self.truncated = 0
        self.closed = False

    def target_columns(self, s, t):
        return self._tcols

    def truncate(self, s, t):
        self.truncated += 1

    def bulk_insert(self, s, t, cols, rows):
        rows = list(rows)
        self.inserts.append((list(cols), rows))
        return len(rows)

    def reset_identity(self, s, t):
        pass

    def close(self):
        self.closed = True


@pytest.fixture
def wire(monkeypatch, tmp_path):
    """Wire fake engines + a temp workspace into migrate_data so _copy_unit (which
    re-loads engines from config in its worker) uses the fakes."""
    def _wire(source, target):
        monkeypatch.setattr(md.config, "workspace_dir", lambda project: tmp_path)
        monkeypatch.setattr(md, "load_pair", lambda: object())
        monkeypatch.setattr(md.engines, "get_source_engine", lambda pair: source)
        monkeypatch.setattr(md.engines, "get_target_engine", lambda pair: target)
        return tmp_path
    return _wire


def _unit(chunks, **over):
    u = {"schema": "APP", "table": "T", "shard": None, "pk": ["ID"],
         "tgt_cols": ["id", "name"], "batch_size": 1000, "project": "proj"}
    u.update(over)
    return u


def _two_chunk_source():
    chunks = [("q0", {"lo": 0}), ("q1", {"lo": 10})]
    rows = {"q0": [(1, "a")], "q1": [(2, "b"), (3, "c")]}
    return FakeSource([("ID", "int"), ("NAME", "varchar")], ["ID"], chunks, rows), chunks


# ---- H3 + VIRTUAL: column alignment via _plan_units ----------------------

def test_plan_units_missing_target_column_raises(wire):
    source = FakeSource([("ID", "int"), ("NAME", "varchar")], ["ID"])
    target = FakeTarget(["id"])  # missing 'name'
    wire(source, target)
    with pytest.raises(RuntimeError) as ei:
        md._plan_units(source, target, "APP", "T", 1, 1000, "proj", truncate=False)
    assert "name" in str(ei.value) and "missing" in str(ei.value).lower()


def test_plan_units_absent_target_table_raises(wire):
    source = FakeSource([("ID", "int")], ["ID"])
    target = FakeTarget([])  # table not created yet
    wire(source, target)
    with pytest.raises(RuntimeError) as ei:
        md._plan_units(source, target, "APP", "T", 1, 1000, "proj", truncate=False)
    assert "not found" in str(ei.value)


def test_plan_units_excludes_virtual_column_from_copy(wire):
    """The bug fix: a source virtual column maps to a target GENERATED column.
    data_columns already drops it, so tgt_cols must NOT contain it — otherwise the
    COPY/INSERT into the generated column fails the whole table."""
    # data_columns has already excluded the virtual column FULL_NAME.
    source = FakeSource([("ID", "int"), ("FIRST", "varchar"), ("LAST", "varchar")],
                        ["ID"])
    # target still HAS the generated column full_name in its catalog.
    target = FakeTarget(["id", "first", "last", "full_name"])
    wire(source, target)
    units = md._plan_units(source, target, "APP", "T", 1, 1000, "proj", truncate=False)
    assert len(units) == 1
    assert units[0]["tgt_cols"] == ["id", "first", "last"]
    assert "full_name" not in units[0]["tgt_cols"]


# ---- STATS: _plan_units uses the estimate to size shards -----------------

def test_plan_units_caps_shards_by_estimate(wire):
    # Wide PK span (0..200M) but only 100k estimated rows -> 2 shards, not 16.
    source = FakeSource([("ID", "int"), ("NAME", "varchar")], ["ID"],
                        bounds=(0, 200_000_000), estimate=100_000)
    target = FakeTarget(["id", "name"])
    wire(source, target)
    units = md._plan_units(source, target, "APP", "T", 16, 50_000, "proj",
                           truncate=False)
    assert len(units) == 2
    assert [u["shard"] for u in units] == [0, 1]
    # ranges are contiguous and cover the whole span
    assert units[0]["pk_lo"] == 0 and units[-1]["pk_hi"] == 200_000_000 + 1


def test_plan_units_small_table_not_sharded(wire):
    source = FakeSource([("ID", "int"), ("NAME", "varchar")], ["ID"],
                        bounds=(0, 200_000_000), estimate=1_000)  # tiny
    target = FakeTarget(["id", "name"])
    wire(source, target)
    units = md._plan_units(source, target, "APP", "T", 16, 50_000, "proj",
                           truncate=False)
    assert len(units) == 1 and units[0]["shard"] is None


# ---- happy path + H1/H2 resume (via _copy_unit) --------------------------

def test_full_copy_writes_complete_state(wire):
    source, chunks = _two_chunk_source()
    target = FakeTarget(["id", "name"])
    wire(source, target)
    r = md._copy_unit(_unit(chunks))
    assert r["status"] == "ok" and r["copied"] == 3
    assert len(target.inserts) == 2
    state = md._load_state(md._wm_path("proj", "APP", "T", None))
    assert state["complete"] is True
    assert state["signature"] == md._chunk_signature(chunks)
    assert state["copied"] == 3
    # inserts use the lower-cased target column names supplied in the unit
    assert target.inserts[0][0] == ["id", "name"]


def test_resume_skips_committed_chunks_when_signature_matches(wire):
    source, chunks = _two_chunk_source()
    target = FakeTarget(["id", "name"])
    wire(source, target)
    md._save_state(md._wm_path("proj", "APP", "T", None),
                   {"signature": md._chunk_signature(chunks), "done_chunks": 1,
                    "copied": 1, "complete": False})
    r = md._copy_unit(_unit(chunks))
    assert r["status"] == "ok"
    assert len(target.inserts) == 1                 # only chunk 1 (q1) re-copied
    assert target.inserts[0][1] == [(2, "b"), (3, "c")]
    assert target.truncated == 0


def test_complete_state_is_skipped(wire):
    source, chunks = _two_chunk_source()
    target = FakeTarget(["id", "name"])
    wire(source, target)
    md._save_state(md._wm_path("proj", "APP", "T", None),
                   {"signature": md._chunk_signature(chunks), "done_chunks": 2,
                    "copied": 3, "complete": True})
    r = md._copy_unit(_unit(chunks))
    assert r["status"] == "skipped" and r["copied"] == 3
    assert target.inserts == []                     # nothing re-copied


def test_shard_resume_state_is_isolated_per_shard(wire):
    """Two shards of the same table must not share resume state (regression guard
    for the shard-suffixed watermark path)."""
    source, chunks = _two_chunk_source()
    target = FakeTarget(["id", "name"])
    wire(source, target)
    # Mark shard 0 complete; shard 1 must still copy.
    md._save_state(md._wm_path("proj", "APP", "T", 0),
                   {"signature": md._chunk_signature(chunks), "done_chunks": 2,
                    "copied": 3, "complete": True})
    r0 = md._copy_unit(_unit(chunks, shard=0))
    r1 = md._copy_unit(_unit(chunks, shard=1))
    assert r0["status"] == "skipped"
    assert r1["status"] == "ok" and r1["copied"] == 3


# ---- base-engine data_columns + adaptive step (real logic) ---------------

class _MiniEngine(SourceEngine):
    """Concrete SourceEngine implementing only what the base data_columns /
    _adaptive_chunk_step logic needs; the rest are trivial stubs so the ABC can be
    instantiated."""

    def __init__(self, cols, virtual):
        self._cols = cols
        self._virtual = set(virtual)

    # the two methods under test rely on these:
    def table_columns(self, schema, table):
        return self._cols

    def virtual_columns(self, schema, table):
        return set(self._virtual)

    # ---- unused abstract stubs ----
    def connect(self): return None
    def ping_sql(self): return "SELECT 1"
    def server_version(self): return "x"
    def list_tables(self, schema, only=None): return []
    def get_table_list(self, schema): return []
    def extract_object_unit(self, schema, table): return None
    def extract_code_objects(self, schema): return []
    def list_callables(self, schema): return []
    def code_object_ddl(self, schema, object_type, name): return ""
    def sample_rows(self, schema, table, n=5): return [], []
    def primary_key_columns(self, schema, table): return []
    def chunk_iterator(self, schema, table, pk_cols, batch_size,
                       pk_lo=None, pk_hi=None): return iter(())
    def inventory(self, schema): return {}
    def count_rows(self, schema, table): return 0
    def foreign_key_deps(self, schema, tables): return {}


def test_data_columns_excludes_virtual_case_insensitive():
    eng = _MiniEngine([("ID", "int"), ("FIRST", "varchar"), ("LAST", "varchar"),
                       ("FULL_NAME", "varchar")],
                      virtual={"full_name"})  # note: different case than catalog
    assert eng.data_columns("S", "T") == [("ID", "int"), ("FIRST", "varchar"),
                                          ("LAST", "varchar")]


def test_data_columns_no_virtual_returns_all():
    eng = _MiniEngine([("ID", "int"), ("NAME", "varchar")], virtual=set())
    assert eng.data_columns("S", "T") == [("ID", "int"), ("NAME", "varchar")]


def test_adaptive_chunk_step_sparse_range_widens_step():
    eng = _MiniEngine([], virtual=set())
    # 200M-wide range, 100k rows, 50k batch -> step targets ~batch rows:
    #   step = 50_000 * (200_000_000 / 100_000) = 100_000_000
    step = eng._adaptive_chunk_step(1, 200_000_000, 50_000, 100_000)
    assert step == 100_000_000
    # so the whole range is covered in ~2 chunks instead of 4000 empty ones
    span = 200_000_000
    chunks = -(-span // step)  # ceil division
    assert chunks == 2


def test_adaptive_chunk_step_dense_range_is_unchanged():
    eng = _MiniEngine([], virtual=set())
    # span == estimate (dense): step stays at batch_size (legacy behaviour)
    assert eng._adaptive_chunk_step(1, 100_000, 50_000, 100_000) == 50_000


def test_adaptive_chunk_step_unknown_estimate_is_unchanged():
    eng = _MiniEngine([], virtual=set())
    assert eng._adaptive_chunk_step(1, 200_000_000, 50_000, -1) == 50_000


def test_adaptive_chunk_step_capped_at_span():
    eng = _MiniEngine([], virtual=set())
    # extremely sparse, but batch_size (100) <= span (1000): the density widening
    # is capped at the span so a single chunk covers the whole range.
    step = eng._adaptive_chunk_step(0, 999, 100, 1)
    assert step == 1000  # == span (hi - lo + 1)
