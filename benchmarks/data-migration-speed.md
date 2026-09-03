# Benchmark — `dbmig migrate-data` speed (Oracle → Aurora PostgreSQL)

Measures the throughput of the toolkit's built-in data mover (`dbmig migrate-data`) at
~100 GB, and what does (and does **not**) speed it up. **v1 headline: the original mover
sustained ~15–20 MB/s and did *not* scale with `--workers` (thread-per-table, single-stream
per table).** The [**v2 parallel path**](#v2--parallel-data-path-implemented) below
(process-based parallelism + intra-table PK sharding + read/write pipelining) addresses that;
for production-scale movement the framework still hands off to AWS DMS (full-load + CDC).

## Setup

| Component | Configuration |
|---|---|
| Source | RDS Oracle 19c, `db.r6i.xlarge`, gp3 **400 GB / 12000 IOPS / 500 MB/s**, `us-east-1a` |
| Target | Aurora PostgreSQL 17.7, **Serverless v2 (2–64 ACU)**, writer in `us-east-1b` |
| Compute | EC2 **`m7i.4xlarge`** (16 vCPU, 12.5 Gbps) running `dbmig`, `us-east-1a` (same AZ as source) |
| Data | rows ≈ **1.1 KB** (`id bigint`, `filler varchar(1000)`, `n1 numeric`, `d1 timestamp`) |
| Tool | `python -m dbmig migrate-data` (PK-range chunked, psycopg `COPY`), `--truncate` per run |

Row shape and scenarios were chosen per the request: **(1) one ~100 GB table**, and
**(2) ten ~10 GB tables** (to exercise parallelism). Source and the EC2 running the tool are
in the **same AZ**; the Aurora Serverless v2 writer sits in `us-east-1b` (AZ noted below).

> Throughput is reported as the **sustained rate** over a 12–24 GB window at steady state.
> A full single-stream 100 GB load runs ≈ 1.5 h at these rates; the rate — not the wall
> clock — is the metric, and it was stable across the window.

## Results

### Scenario 1 — single ~100 GB table (effectively single-stream)

`migrate-data` runs **one worker per table** and copies a table's PK-range chunks
**serially**, so a single table is single-stream regardless of `--workers`.

| Variant | rows/s | ~MB/s | Note |
|---|---|---|---|
| baseline (target PK present, batch 50k) | ~18,200 | ~20 | declines slightly as the PK b-tree grows |
| optimized (target heap/no PK, batch 500k) | ~10,600 | ~12 | **no faster** — so it is *not* target-index-bound |

Dropping the primary key and enlarging the batch did **not** speed up the single table →
the limit is the single fetch→transfer→`COPY` pipeline, not target indexing.

### Scenario 2 — ten ~10 GB tables (`--workers 10`, parallel across tables)

| Variant | rows/s (aggregate) | ~MB/s | Note |
|---|---|---|---|
| `--workers 10`, batch 500k | ~18,000 | ~20 | **≈ same as single-stream** |
| `--workers 10`, batch 500k, `synchronous_commit=off` | ~15,800 | ~17 | no material change |

**Ten parallel workers delivered essentially the same aggregate throughput as one stream.**

### Where the time goes (why it doesn't scale)

Sampled during the 10-worker run:

- **EC2** `m7i.4xlarge`: ~**99% idle**, the `dbmig` process ~9% CPU (of 16 vCPU).
- **Source Oracle**: ~**11–13%** CPU.
- **Target Aurora**: scaled to its **max 64 ACU**, CPU **1–8%**, `WriteThroughput` bursty (6–160 MB/s).

No tier is CPU-bound, yet throughput is flat at ~15–20 MB/s whether 1 or 10 streams. The
data path is **latency-/serialization-bound**: each PK-range chunk is fetched, streamed via
`COPY`, and committed largely in sequence, and the per-table worker threads contend on the
target rather than adding aggregate bandwidth.

## Optimization levers — what we tried

| Lever | Effect here | Takeaway |
|---|---|---|
| More workers (1 → 10) | ~none (18k ≈ 18k rows/s) | per-table threads don't add aggregate throughput on this path |
| Drop target PK + larger batch (scenario 1) | ~none | load is not target-index-bound for this shape |
| `synchronous_commit=off` (target DB) | ~none | not commit-durability-bound |
| Same-AZ source + EC2 | baseline (used throughout) | keep compute co-located with the source (latency-sensitive chunked reads) |

## Recommendations

1. **Use AWS DMS for production-scale loads.** The framework already positions `migrate-data`
   as a dev/test loader and hands off to AWS DMS (full-load + CDC) for real volume. This
   benchmark quantifies why: the built-in mover tops out ~15–20 MB/s and does not scale with
   workers.
2. **For a single very large table**, there is **no intra-table parallelism** — it is one
   stream. Split/partition it (parallel PK ranges) or move it with AWS DMS. A worthwhile
   toolkit enhancement is intra-table range parallelism.
3. **Toolkit data-path optimizations** (future work): overlap fetch and `COPY` (pipeline
   rather than per-chunk sequential), reduce per-row Python overhead in the `COPY` writer
   (block/binary `COPY`), larger source `arraysize`, and **process-based** parallelism so
   independent tables truly run in parallel.
4. **Target placement & type:** co-locate the target in the **same AZ** as the source/compute
   (here the Serverless v2 writer was in `us-east-1b`, one AZ away — adding per-operation
   latency to a latency-bound path), and prefer a **provisioned** writer with tuned
   WAL/commit settings for throughput-sensitive bulk loads.
5. **Keep the secondary-object drop/recreate** (`capture-target-objects` → `pre-load-drop`
   → load → `post-load-restore`) for any bulk load — it removes index/FK maintenance from the
   load window (orthogonal to the single-stream limit measured here).

## v2 — parallel data path (implemented)

The v1 results above (single-stream, thread-per-table) are the **"before"**. The three
future-work levers named in the recommendations are now **shipped** in `migrate-data`, all
keeping the `COPY` fast path:

1. **Process-based parallelism.** Work units run in a `ProcessPoolExecutor`, so each
   concurrent copy gets its own interpreter/GIL and CPU core. A thread pool shares one GIL,
   and the per-row `COPY` marshaling then serializes — which is why v1's `--workers 10`
   delivered single-stream throughput. `--mode-parallel process` is the default;
   `--mode-parallel thread` keeps the legacy pool for A/B comparison.

2. **Intra-table PK sharding.** A large table with a single numeric PK is split into
   `--shards N` disjoint half-open PK ranges `[a, b)`, each a separate work unit / process,
   so **one huge table is read by many parallel streams** (the scenario-1 gap). Shard ranges
   are derived from `MIN(pk)`/`MAX(pk)`; non-shardable tables (composite / non-numeric / no
   PK, or small) stay a single unit. Each shard chunks *within* its range and clamps every
   chunk's upper bound to the shard boundary so ranges never overlap.

3. **Read/write pipelining.** Within a unit the source fetch runs on a producer thread
   feeding a bounded row queue while the `COPY` consumer drains it, so source-read
   round-trips overlap the target write instead of alternating on one thread (the
   latency-bound "everything idle, still slow" symptom).

Resume, `--truncate`, source→target column alignment, FK-dependency load ordering (parents
before children), and post-load identity/`AUTO_INCREMENT` reset are all preserved. Resume
state is now **per (schema, table, shard)** so an interrupted sharded load resumes each shard
independently; a plain `COPY` (no `ON CONFLICT`) means a re-run without `--truncate` safely
**skips** already-completed shards rather than duplicating rows.

```bash
# one 100 GB table, split into 16 parallel PK-range streams across 16 processes
python -m dbmig migrate-data --schema BENCH --tables T1 \
  --shards 16 --workers 16 --batch-size 100000 --truncate

# ten 10 GB tables, each split into 4 shards (40 units), 16 processes at a time
python -m dbmig migrate-data --schema BENCH --tables S1,...,S10 \
  --shards 4 --workers 16 --batch-size 100000 --truncate
```

**Correctness** was verified end-to-end against live Aurora PostgreSQL + Oracle before
benchmarking: a 4-shard process-mode load of a 50 000-row single-numeric-PK table produced
exactly 50 000 distinct rows with no duplicates; a re-run without `--truncate` copied 0 new
rows and resumed all 4 shards; thread-mode produced identical results.

### Results — v2 (parallel path)

Re-measured on the same-AZ setup (EC2 `m7i.4xlarge` + Oracle in `us-east-1a`, Aurora PG
Serverless v2 writer in `us-east-1b`), rows ≈ 1.1 KB, full loads with `--truncate`.

**Scenario 1 — single ~19.7 GB table (18 M rows, single numeric PK):**

| Variant | Mode / shards / workers | Time | rows/s | ~MB/s | vs baseline |
|---|---|---|---|---|---|
| baseline (v1 single-stream) | thread / 1 / 1 | 1633 s | ~11,000 | ~12 | 1.0× |
| v2 | process / 8 / 8 | 259 s | ~69,500 | ~76 | **6.3×** |
| v2 | process / 16 / 16 | 227 s | ~79,300 | ~87 | **7.2×** |
| v2 | thread / 16 / 16 | 232 s | ~77,600 | ~85 | 7.0× |

**Scenario 2 — eight ~2.2 GB tables (16 M rows total), one stream per table:**

| Variant | Mode / shards / workers | Time | rows/s | ~MB/s |
|---|---|---|---|---|
| v2 | thread / 1 / 8 | 203 s | ~78,800 | ~88 |
| v2 | process / 1 / 8 | 198 s | ~80,800 | ~90 |

### What actually moved the needle (honest reading)

- **~7× on the single large table.** The v1 killer — *no intra-table parallelism* — is gone:
  16 PK-range shards turn one table into 16 concurrent streams and it reaches the same
  aggregate as eight independent tables.
- **The dominant levers are sharding + pipelining, not process-vs-thread.** On the single
  table, thread-mode (232 s) and process-mode (227 s) with 16 shards are within ~2% of each
  other, and scenario 2 is the same in both modes. At this scale the load is **network- and
  target-I/O bound at ~85–90 MB/s**, not CPU/GIL-bound — so once the fetch and `COPY` are
  pipelined and enough streams exist to saturate the link, the GIL is no longer the limiter
  and processes vs threads is a wash.
- **Read/write pipelining lifts the floor across the board.** v1's per-table thread copied a
  chunk by alternating fetch and `COPY` on one thread, so eight threads still summed to
  ~single-stream (~18 K rows/s). v2's per-unit producer thread overlaps the source read with
  the `COPY` write, so eight streams now reach ~88 MB/s even in thread mode.
- **Why `process` is still the default.** It costs nothing here and keeps headroom for the
  cases this environment did not stress: CPU-heavy per-row conversion (wide rows, type
  coercion, text encoding) and higher-bandwidth links, where the per-row marshaling *would*
  hit the GIL and separate cores matter. `--mode-parallel thread` remains for constrained
  or spawn-averse environments (and A/B).
- **Diminishing returns past the link ceiling.** 8→16 shards on the single table gained only
  ~14% (76→87 MB/s): the ~85–90 MB/s ceiling (partly the cross-AZ Serverless-v2 target) is
  the real cap. Co-locating a provisioned target in the source AZ would raise it.

**Bottom line:** for a large single table the built-in mover went from ~12 MB/s to ~87 MB/s
(**~7×**) with `--shards 16 --workers 16`; multi-table loads reach the same ~90 MB/s. The
built-in mover is now viable for substantially larger dev/test loads, though AWS DMS remains
the path for production-scale movement and CDC.

## Reproduce

```bash
# same-AZ EC2 with the toolkit + connections.yaml (Oracle source, Aurora PG target)
# generate:  gen.py --tables 1  --rows 18000000 --prefix T   # scenario 1 (~20 GB)
#            gen.py --tables 8  --rows 2000000  --prefix S    # scenario 2 (8 x ~2.2 GB)

# v1 single-stream reference
python -m dbmig migrate-data --schema BENCH --tables T1 \
  --workers 1 --shards 1 --mode-parallel thread --batch-size 100000 --truncate

# v2 single big table: 16 PK-range shards across 16 processes (~7x)
python -m dbmig migrate-data --schema BENCH --tables T1 \
  --workers 16 --shards 16 --batch-size 100000 --truncate

# v2 many tables: one stream per table, 8 at a time
python -m dbmig migrate-data --schema BENCH --tables S1,S2,S3,S4,S5,S6,S7,S8 \
  --workers 8 --shards 1 --batch-size 100000 --truncate
```

_Measured Sep 2026 in the workshop account. v1 (single-stream) numbers used a ~100 GB shape;
the v2 comparison used a ~20 GB single table and 8 × ~2.2 GB tables (same row shape, same-AZ
source/compute, cross-AZ Serverless-v2 target) sized so full loads complete quickly — the
**rate** (which was stable across the load), not the wall clock, is the metric. Numbers are
environment-specific (instance classes, Serverless v2 ceiling, cross-AZ target) and
characterize behavior and scaling, not absolute maxima._
