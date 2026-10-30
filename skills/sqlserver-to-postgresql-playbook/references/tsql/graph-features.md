# Graph Features

> Source: AWS SQL Server→Aurora PostgreSQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/sql-server-to-aurora-postgresql-migration-playbook/chap-sql-server-aurora-pg.tsql.graph.html

**Conversion category:** Manual (two-star feature compatibility, no automation — no native support, rewrite required)
**SCT automation:** No automation; N/A action code

> **Reviewed for Aurora PostgreSQL 18** (validated on 18.6, 2026-10-29): Added verified join/recursive-CTE patterns with SEARCH/CYCLE, pgrouting availability, Apache AGE not available, edge-constraint mapping.

## SQL Server

SQL Server (2017+) offers graph database capabilities to model many-to-many relationships, integrated into T-SQL. A graph is a collection of nodes/vertices (entities) and edges/relationships. Distinguishing features:
- Edges are first-class entities and can have properties.
- A single edge can connect multiple nodes.
- Easy pattern matching and multi-hop navigation queries.
- Easy transitive closure and polymorphic queries.

Choose graph over relational when: hierarchical data (beyond `HierarchyID` limits, e.g., multiple parents per node), complex evolving many-to-many relationships, or analysis of interconnected data.

SQL Server 2017 added `CREATE TABLE ... AS NODE`/`AS EDGE` and the `MATCH` keyword:

```sql
CREATE TABLE Person (ID INTEGER PRIMARY KEY, Name VARCHAR(100), Age INT) AS NODE;
CREATE TABLE friends (StartDate date) AS EDGE;
```

`MATCH` uses ASCII-art pattern syntax:

```sql
-- Find friends of John
SELECT Person2.Name
FROM Person Person1, Friends, Person Person2
WHERE MATCH(Person1-(Friends)->Person2)
AND Person1.Name = 'John';
```

SQL Server 2019 added cascaded delete on edge constraints (data integrity), plus table/index partitioning for graph tables.

## PostgreSQL

PostgreSQL has **no native graph database feature**. You can implement some graph behavior using:
- **Recursive CTE queries** (`WITH RECURSIVE`) for traversal/multi-hop navigation.
- **Serializing graphs to regular relations** (node and edge tables modeled conventionally).

## PostgreSQL 18 patterns (verified on Aurora PostgreSQL 18.6)

`MATCH(Person1-(Friends)->Person2)` becomes a join through an edge table; multi-hop `SHORTEST_PATH` / transitive closure becomes a recursive CTE. Since PG 14 the standard `SEARCH` and `CYCLE` clauses replace hand-built path arrays:

```sql
CREATE TABLE person  (id int PRIMARY KEY, name text);
CREATE TABLE friends (src int REFERENCES person ON DELETE CASCADE,   -- edge constraint + cascade
                      dst int REFERENCES person ON DELETE CASCADE,
                      startdate date, PRIMARY KEY (src, dst));

-- friends of John (1 hop)
SELECT p2.name FROM person p1 JOIN friends f ON f.src = p1.id JOIN person p2 ON p2.id = f.dst
WHERE p1.name = 'John';

-- everyone reachable from John, breadth first, stopping at cycles
WITH RECURSIVE g(id, depth) AS (
  SELECT dst, 1 FROM friends WHERE src = 1
  UNION ALL
  SELECT f.dst, g.depth + 1 FROM g JOIN friends f ON f.src = g.id)
SEARCH BREADTH FIRST BY id SET ord
CYCLE id SET is_cycle USING path
SELECT id, depth FROM g WHERE NOT is_cycle ORDER BY ord;
```

- Index both edge columns (`(src, dst)` and `(dst)`); recursive traversal does an index lookup per hop.
- SQL Server's implicit `$node_id`/`$edge_id` pseudo-columns have no equivalent; use the node primary key.
- Apache AGE (openCypher in PostgreSQL) is **not** available on Aurora PostgreSQL 18.6. `pgrouting` 3.8 is available and gives shortest-path algorithms (`pgr_dijkstra`) over an edge table.
- SQL:2023 property-graph queries (`GRAPH_TABLE`) are not in PostgreSQL 18.

## Conversion notes
- No native equivalent — rewrite the application's graph logic.
- Model nodes and edges as ordinary tables; replace `MATCH` pattern queries with joins and `WITH RECURSIVE` CTEs (with `SEARCH`/`CYCLE`) for multi-hop/transitive traversal; `SHORTEST_PATH` → recursive CTE or `pgr_dijkstra`.
- Edge constraints with cascaded delete → foreign keys `ON DELETE CASCADE` on the edge table.
- For demanding graph workloads, consider a dedicated graph database (e.g., Amazon Neptune) outside Aurora PostgreSQL.
