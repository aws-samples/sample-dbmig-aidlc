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

## v3 — FDW push-down path (`--method fdw`, cloud-to-cloud)

Everything above measures the **`toolkit`** method (the default): the host running `dbmig`
pulls every row from the source and pushes it into the target. That is fine when the toolkit
runs *inside* the cloud (the same-AZ EC2 above reached ~85–90 MB/s), but it collapses when the
toolkit host sits **on-premises across a slow VPN** — every row crosses the VPN **twice**
(source → toolkit → target), so the VPN, not the databases, sets the ceiling.

The **`--method fdw`** path removes the toolkit host from the data path entirely. The *target*
Aurora PostgreSQL reads directly from the source through a foreign data wrapper (`oracle_fdw`
for Oracle, `tds_fdw` for SQL Server): the toolkit only issues control SQL
(`CREATE SERVER`/`FOREIGN TABLE`, then `INSERT INTO <target> SELECT FROM <foreign_table>`),
while the bulk data moves **source → target server-side, cloud-to-cloud**. Intra-table PK
sharding (`--shards`) still applies — each shard is one concurrent server-side `INSERT … SELECT`
over a disjoint PK range (pushed down to the source).

### Setup (this measurement)

Deliberately measured from the **worst-case topology the feature targets**: the `dbmig` host
was a workstation connected to the workshop VPC **over a VPN** (not an in-VPC EC2), so the
`toolkit` numbers here are VPN-bound by design. Source/target are the same instances as above
(RDS Oracle 19c → Aurora PostgreSQL 17.7, `us-east-1`). One table, single numeric PK, rows
≈ 1.03 KB (`id bigint`, `filler varchar(1000)`, `n1 numeric`, `d1 timestamp`), **1,000,000 rows
≈ 1.03 GB**, full loads with `--truncate`. The Aurora Serverless v2 target was pinned at
**16–64 ACU** for this run (see the ACU note below).

| Method | shards / workers | Time | rows/s | ~MB/s | Data path |
|---|---|---|---|---|---|
| `toolkit` (from VPN host) | 16 / 16 | 359.4 s | ~2,780 | ~2.9 | source → **VPN** → toolkit → **VPN** → target |
| `fdw` | 8 / 8 | 29.7 s | ~33,600 | ~34.6 | source → target (server-side); toolkit issues control SQL only |
| `fdw` | 16 / 16 | 30.7 s | ~32,600 | ~33.5 | source → target (server-side) |

**≈12× faster in this VPN-bound scenario — and the FDW rate does not depend on the toolkit
host's link at all.** `fdw` at 8 vs 16 shards is within noise (~34 vs ~33 MB/s): past ~8
concurrent server-side streams the limit is the source fetch / target write, not shard count.
The `fdw` figures include the fixed setup/teardown cost (create the
extension/server/user-mapping/foreign-table, then `DROP … CASCADE` afterwards); the `toolkit`
figure is pure VPN-bound transfer.

> **Serverless v2 ACU matters — a lot.** An earlier pass at only **200 MB** against a target
> floored at **1 ACU** measured `fdw` at just ~8–9 MB/s. That was two confounds stacked: (1)
> Serverless v2 scales *reactively*, so a ~25 s load never gave it time to ramp from the 1-ACU
> floor, and (2) at 200 MB the fixed create/drop overhead is a large fraction of the run.
> Pinning the floor to **16 ACU** (≈ an `r8g.xlarge`-class writer) and using **1 GB** removed
> both and lifted `fdw` to ~33–35 MB/s. If you benchmark this yourself on Serverless v2, set a
> realistic ACU floor and use ≥1 GB or the numbers are dominated by scaling lag and overhead.

Read this the right way: this is **not** a claim that `oracle_fdw` beats an in-VPC toolkit —
the same-AZ EC2 `toolkit` (v2 above) hit ~85–90 MB/s, well above the ~33 MB/s server-side FDW
rate seen here. FDW's `INSERT … SELECT` goes through the normal row executor (per-row + WAL +
PK-index maintenance), whereas the toolkit uses the `COPY` fast path; and each `oracle_fdw`
stream fetches over OCI one batch at a time. The point is **topological**: when the toolkit
host is on a slow/remote link you **cannot** reach those in-VPC rates with `toolkit`, whereas
`fdw` keeps the data movement cloud-side regardless of where `dbmig` runs. **Choose `fdw`**
when source and target are both in the cloud but the toolkit host is not (or is far away);
**choose `toolkit`** (or AWS DMS) when `dbmig` runs in-VPC/in-AZ; **choose AWS DMS** for
production-scale volume and CDC either way.

### Correctness (verified live)

**Oracle → PostgreSQL (`oracle_fdw`).** A 5,000-row, 4-shard `fdw` load produced an **exact
row-count match** and identical aggregates vs the source (`SUM(id)`, `SUM(n1)`, `filler`
length), confirming the SOURCE→TARGET column mapping (Oracle `UPPER` → PostgreSQL `lower`) and
value fidelity. A re-run without `--truncate` copied **0 new rows** (all 4 shards resumed).
Foreign tables were created only in the isolated staging schema `dbmig_fdw_demo` (never the
`demo` data schema), and the default teardown dropped the server + staging schema and **removed
the source credentials** stored in the user mapping.

**SQL Server → PostgreSQL (`tds_fdw`), live.** Against a real SQL Server 2019 instance
(`tds_fdw 2.0.4` on the same Aurora target), AdventureWorks-style **`Person.Person`** (incl. a
`datetime`) and **`HumanResources.Employee`** (incl. two `date`, a `datetime`, and a `bit`),
**50,000 rows each, 4 shards**, both loaded to an **exact row-count match with sample values
identical to the source**. This exercised the SQL Server specifics: mixed-case schema/column
names (`BusinessEntityID` → `businessentityid`) resolved by `match_column_names`, `bit` →
`boolean`, and a **temporal-type quirk** — `tds_fdw` returns `date`/`datetime` as locale
strings (e.g. `Jan  1 1985 12:00:00:AM`) that PostgreSQL will not ingest directly, so for a
SQL Server source the loader declares temporal foreign columns as `text` and normalizes +
casts them on the target side (preserving sub-second precision and the fast sharded path).

### Reproduce (FDW)

```bash
# dbmig host anywhere (on-prem/VPN or in-VPC); Oracle source + Aurora PG target reachable.
# default method is 'toolkit'; select the push-down path with --method fdw.

# one big single-numeric-PK table, 16 server-side PK-range streams
python -m dbmig migrate-data --schema DEMO --tables T1 \
  --method fdw --shards 16 --workers 16 --truncate --project demo

# keep the FDW objects for inspection/repeat runs (leaves source creds on the target!) …
python -m dbmig migrate-data --schema DEMO --tables T1 \
  --method fdw --shards 16 --workers 16 --truncate --fdw-keep --project demo
# … then remove them (server CASCADE + staging schema) when done:
python -m dbmig migrate-data --schema DEMO --method fdw --fdw-cleanup --project demo
```

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
