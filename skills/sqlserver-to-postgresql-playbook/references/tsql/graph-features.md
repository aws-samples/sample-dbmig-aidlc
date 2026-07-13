# Graph Features

> Source: AWS SQL Server→Aurora PostgreSQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/sql-server-to-aurora-postgresql-migration-playbook/chap-sql-server-aurora-pg.tsql.graph.html

**Conversion category:** Manual (two-star feature compatibility, no automation — no native support, rewrite required)
**SCT automation:** No automation; N/A action code

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

## Conversion notes
- No native equivalent — rewrite the application's graph logic.
- Model nodes and edges as ordinary tables; replace `MATCH` pattern queries with joins and `WITH RECURSIVE` CTEs for multi-hop/transitive traversal.
- For demanding graph workloads, consider a dedicated graph database (e.g., Amazon Neptune) outside Aurora PostgreSQL.
