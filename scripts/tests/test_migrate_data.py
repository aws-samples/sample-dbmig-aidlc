"""Tests for ``dbmig migrate-data`` resume/durability and column alignment.

Covers the review's highest-risk, previously-untested module:
  * H1 — resume is gated on a chunk-boundary signature, so ordinal skipping only
    happens when boundaries are provably identical; a mismatch (source mutated or
    --batch-size changed) triggers a clean truncate+reload instead of silent
    drop/duplication.
  * H2 — resume state is written atomically (temp file + os.replace) and leaves no
    stray temp files.
  * H3 — a source column missing from the converted target table fails the copy
    loudly and early, before any rows are streamed.
"""
import json

import pytest

from dbmig.commands import migrate_data as md


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


# ---- fakes for _copy_one_table -------------------------------------------

class FakeSource:
    def __init__(self, cols, pk, chunks, rows_by_sql):
        self._cols = cols
        self._pk = pk
        self._chunks = chunks
        self._rows = rows_by_sql
        self.closed = False

    def table_columns(self, s, t):
        return self._cols

    def primary_key_columns(self, s, t):
        return self._pk

    def chunk_iterator(self, s, t, pk, bs):
        return iter(self._chunks)

    def fetch_iter(self, sql, params):
        return iter(self._rows.get(sql, []))

    def get_table_list(self, s):
        return []

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
    """Wire fake engines + a temp workspace into migrate_data."""
    def _wire(source, target):
        monkeypatch.setattr(md.config, "workspace_dir", lambda project: tmp_path)
        monkeypatch.setattr(md.engines, "get_source_engine", lambda pair: source)
        monkeypatch.setattr(md.engines, "get_target_engine", lambda pair: target)
        return tmp_path
    return _wire


def _two_chunk_source():
    chunks = [("q0", {"lo": 0}), ("q1", {"lo": 10})]
    rows = {"q0": [(1, "a")], "q1": [(2, "b"), (3, "c")]}
    return FakeSource([("ID", "int"), ("NAME", "varchar")], ["ID"], chunks, rows), chunks


# ---- H3: column alignment ------------------------------------------------

def test_missing_target_column_fails_loudly(wire):
    source, _ = _two_chunk_source()
    target = FakeTarget(["id"])  # missing 'name'
    wire(source, target)
    r = md._copy_one_table("p", "APP", "T", 1000, "proj", truncate=False)
    assert r["status"] == "error"
    assert "name" in r["error"] and "missing" in r["error"].lower()
    assert target.inserts == []  # nothing streamed


def test_absent_target_table_fails(wire):
    source, _ = _two_chunk_source()
    target = FakeTarget([])  # table not created yet
    wire(source, target)
    r = md._copy_one_table("p", "APP", "T", 1000, "proj", truncate=False)
    assert r["status"] == "error"
    assert "not found" in r["error"]


# ---- happy path + H1/H2 resume -------------------------------------------

def test_full_copy_writes_complete_state(wire):
    source, chunks = _two_chunk_source()
    target = FakeTarget(["id", "name"])
    ws = wire(source, target)
    r = md._copy_one_table("p", "APP", "T", 1000, "proj", truncate=False)
    assert r["status"] == "ok" and r["copied"] == 3
    assert len(target.inserts) == 2
    state = md._load_state(md._wm_path("proj", "APP", "T"))
    assert state["complete"] is True
    assert state["signature"] == md._chunk_signature(chunks)
    assert state["copied"] == 3
    # inserts use lower-cased target column names
    assert target.inserts[0][0] == ["id", "name"]


def test_resume_skips_committed_chunks_when_signature_matches(wire):
    source, chunks = _two_chunk_source()
    target = FakeTarget(["id", "name"])
    wire(source, target)
    # Seed state: chunk 0 already committed on a prior run (boundaries identical).
    md._save_state(md._wm_path("proj", "APP", "T"),
                   {"signature": md._chunk_signature(chunks), "done_chunks": 1,
                    "copied": 1, "complete": False})
    r = md._copy_one_table("p", "APP", "T", 1000, "proj", truncate=False)
    assert r["status"] == "ok"
    # only chunk 1 (q1) is copied on resume
    assert len(target.inserts) == 1
    assert target.inserts[0][1] == [(2, "b"), (3, "c")]
    assert target.truncated == 0


def test_signature_mismatch_truncates_and_reloads(wire):
    source, _ = _two_chunk_source()
    target = FakeTarget(["id", "name"])
    wire(source, target)
    # Seed state with a stale signature (source mutated / batch-size changed).
    md._save_state(md._wm_path("proj", "APP", "T"),
                   {"signature": "STALE", "done_chunks": 1, "copied": 1,
                    "complete": False})
    r = md._copy_one_table("p", "APP", "T", 1000, "proj", truncate=False)
    assert r["status"] == "ok" and r["copied"] == 3
    assert target.truncated == 1          # cleaned before reload
    assert len(target.inserts) == 2       # both chunks re-copied (no ordinal skip)


def test_complete_state_skips_reload_without_truncate(wire):
    source, chunks = _two_chunk_source()
    target = FakeTarget(["id", "name"])
    wire(source, target)
    md._save_state(md._wm_path("proj", "APP", "T"),
                   {"signature": md._chunk_signature(chunks), "done_chunks": 2,
                    "copied": 3, "complete": True})
    r = md._copy_one_table("p", "APP", "T", 1000, "proj", truncate=False)
    assert r["status"] == "skipped"
    assert r["copied"] == 3
    assert target.inserts == []           # nothing re-copied


def test_truncate_resets_state_and_recopies(wire):
    source, _ = _two_chunk_source()
    target = FakeTarget(["id", "name"])
    wire(source, target)
    md._save_state(md._wm_path("proj", "APP", "T"),
                   {"signature": "whatever", "done_chunks": 2, "copied": 3,
                    "complete": True})
    r = md._copy_one_table("p", "APP", "T", 1000, "proj", truncate=True)
    assert r["status"] == "ok" and r["copied"] == 3
    assert target.truncated == 1
    assert len(target.inserts) == 2
